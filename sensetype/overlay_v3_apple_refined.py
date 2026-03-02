import tkinter as tk
import ctypes
import threading
import math
import random
import time as _time
from collections import deque

from PIL import Image, ImageDraw, ImageFilter, ImageTk

from .i18n import t

# 高 DPI 感知 — 必须在创建任何窗口前调用
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System DPI Aware (fallback)
    except Exception:
        pass


def _dpi_scale() -> float:
    """获取系统 DPI 缩放倍率（96dpi -> 1.0, 144dpi -> 1.5）。"""
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


class Overlay:
    """屏幕底部浮动状态条 — Apple 风格浅色毛玻璃，可鼠标拖动。

    设计语言：macOS Sonoma 通知风格 — 浅色磨砂玻璃、柔和阴影、
    温暖中性色调、Segoe UI 圆润排版、克制的红色录音指示点。

    V3 refinements:
    - Dramatic red dot breathing (size + color pulsing, 0.2–1.0 range)
    - Adaptive gain for volume bars (rolling window, 80th percentile reference)
    - Organic waveform: neighbor smoothing, tapered bars, gradient tips, reflections
    """

    # ── 逻辑尺寸（96dpi 基准） ──
    _BASE_W = 290
    _BASE_H = 44
    _BASE_R = 14          # 稍大圆角，更柔和
    _BASE_MARGIN = 80
    TRANSPARENT_KEY = "#010101"

    # 超采样倍率
    _SS = 3

    # ── 阴影参数 ──
    _SHADOW_OFFSET_Y = 2   # 阴影向下偏移（逻辑 px）
    _SHADOW_BLUR = 8       # 阴影模糊半径（逻辑 px）
    _SHADOW_PAD = 16       # 画布额外 padding 以容纳阴影

    # ══════════════ Apple 风格配色 ══════════════
    # 浅色磨砂玻璃 — 半透明暖白
    BG_TOP = (255, 255, 255)       # 顶部：纯白
    BG_BOTTOM = (243, 243, 248)    # 底部：极浅暖灰（偏紫，macOS 味道）
    FROST_ALPHA = 22               # 噪点纹理 alpha（克制）
    SHADOW_COLOR = (0, 0, 0, 40)   # 柔和投影

    # 边框 — 极细、极浅，仅提示边界
    BORDER_COLOR = (0, 0, 0, 18)   # 几乎看不见的描边

    # 录音指示 — Apple 经典红点
    REC_DOT_COLOR = "#E8433A"      # SF Symbols 红（录音）— 呼吸亮态
    REC_DOT_DIM = "#F2CCC9"        # 明显浅粉（呼吸暗态，比 V2 更浅以增大对比）
    REC_LABEL_COLOR = "#C4372F"    # 标签文字稍深

    # 音量柱 — 温暖柔和的连续渐变色阶
    BAR_IDLE = "#D1D1D6"           # 静默态：系统灰
    BAR_LOW = "#E0C8C0"            # 低音量：温暖淡灰粉
    BAR_MID = "#F09E8C"            # 中间过渡：温暖桃粉
    BAR_HIGH = "#E8685E"           # 高音量：珊瑚红
    BAR_PEAK = "#E8433A"           # 峰值：与录音指示同色系
    BAR_TIP_GLOW = "#FFB8A8"       # 柱顶高光：亮桃色

    # 识别中
    RECOG_TEXT = "#48484A"         # 深灰（systemGray2）
    RECOG_DOT_DIM = "#D1D1D6"     # 浅灰
    RECOG_DOT_HI = "#8E8E93"      # 中灰

    # 结果文字
    RESULT_TEXT = "#1C1C1E"        # 近黑（label color）

    # ── 音量柱尺寸 ──
    _BASE_BAR_W = 3.5              # 稍宽柱子（比 V2 的 3 更丰满）
    _BASE_BAR_GAP = 2.2            # 柱间距微调

    # ── 自适应增益参数 ──
    _GAIN_WINDOW_SEC = 6.0         # 滚动窗口秒数
    _GAIN_PERCENTILE = 0.80        # 参考峰值百分位
    _GAIN_MIN_REF = 0.05           # 最小参考值（防止静音放大）
    _GAIN_DECAY = 0.92             # 参考值指数衰减（平滑下降）
    _GAIN_RISE = 0.3               # 参考值上升速度（快速响应大音量）

    # ── 波形平滑 ──
    _SMOOTH_WEIGHT = 0.3           # 邻居影响权重（0=无平滑，0.5=强平滑）

    # ── 字体 ──
    # Win11 Segoe UI Variable 最佳；Win10 回退 Segoe UI
    FONT_FAMILY = "Segoe UI Variable"
    FONT_FAMILY_FALLBACK = "Segoe UI"

    def __init__(self):
        self._root: tk.Tk | None = None
        self._canvas: tk.Canvas | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._recorder = None
        self._anim_job = None
        self._hide_job = None
        self._state = "hidden"
        self._bg_photo = None
        self._recog_step = 0

        # DPI 缩放（缓存）
        s = _dpi_scale()
        self._s = s
        self.W = int(self._BASE_W * s)
        self.H = int(self._BASE_H * s)
        self.R = int(self._BASE_R * s)
        self.MARGIN = int(self._BASE_MARGIN * s)

        # 阴影 pad（画布要比逻辑区域大，用于绘制投影）
        self._pad = int(self._SHADOW_PAD * s)
        self._canvas_w = self.W + self._pad * 2
        self._canvas_h = self.H + self._pad * 2

        # 字体
        fl = max(7, int(8 * s))
        ft = max(8, int(9.5 * s))
        self._font_label = (self.FONT_FAMILY, fl, "bold")
        self._font_text = (self.FONT_FAMILY, ft)
        # 回退字体（如果 Segoe UI Variable 不可用，tk 会静默降级）

        # 录音区布局（逻辑坐标 * s，相对于 pad 内区域）
        self._dot_cx = self._pad + int(18 * s)
        self._label_x = self._pad + int(32 * s)

        # 音量柱参数
        bw = max(2, int(self._BASE_BAR_W * s))
        bg = max(2, int(self._BASE_BAR_GAP * s))
        self._bw = bw
        self._bstep = bw + bg

        rec_end = self._pad + int(58 * s)
        gap = self._bstep * 3
        self._bar_x0 = rec_end + gap
        self._bar_x1 = self._pad + self.W - int(14 * s)
        self._bar_n = max(4, (self._bar_x1 - self._bar_x0) // self._bstep)

        # 时间线滚动 deque
        self._vol_hist: deque[float] = deque(maxlen=self._bar_n)

        # 自适应增益状态
        self._gain_ref = self._GAIN_MIN_REF       # 当前参考最大值
        # 存储最近几秒的原始音量用于计算百分位
        samples_per_sec = 1000 // 50  # 50ms tick -> 20 samples/sec
        self._gain_window_size = int(self._GAIN_WINDOW_SEC * samples_per_sec)
        self._gain_history: deque[float] = deque(maxlen=self._gain_window_size)

        # 拖动
        self._drag_ox = 0
        self._drag_oy = 0

    # ════════════════ lifecycle ════════════════

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def stop(self):
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    def _run(self):
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.96)
        self._root.config(bg=self.TRANSPARENT_KEY)
        self._root.attributes("-transparentcolor", self.TRANSPARENT_KEY)

        # 画布比逻辑尺寸大，额外空间用于阴影
        self._canvas = tk.Canvas(
            self._root, width=self._canvas_w, height=self._canvas_h,
            bg=self.TRANSPARENT_KEY, highlightthickness=0,
        )
        self._canvas.pack()

        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - self._canvas_w) // 2
        y = sh - self._canvas_h - self.MARGIN + self._pad
        self._root.geometry(f"{self._canvas_w}x{self._canvas_h}+{x}+{y}")

        self._apply_win32_styles()
        self._bg_photo = self._render_bg()
        self._bind_drag()

        self._ready.set()
        self._root.mainloop()

    def _apply_win32_styles(self):
        """Win32: 可交互（拖动）、不抢焦点、不出现在任务栏。"""
        try:
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000

            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self._root.winfo_id())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print(t("overlay.win32_fail", error=e))

    def _bind_drag(self):
        self._canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self._canvas.bind("<B1-Motion>", self._on_drag_move)

    def _on_drag_start(self, ev):
        self._drag_ox = ev.x
        self._drag_oy = ev.y

    def _on_drag_move(self, ev):
        x = self._root.winfo_x() + ev.x - self._drag_ox
        y = self._root.winfo_y() + ev.y - self._drag_oy
        self._root.geometry(f"+{x}+{y}")

    # ════════════════ 背景渲染（3x 超采样 + 投影） ════════════════

    def _render_bg(self):
        S = self._SS
        # 逻辑区域在超采样空间中的尺寸
        w, h, r = self.W * S, self.H * S, self.R * S
        pad = self._pad * S
        # 画布总尺寸（超采样）
        cw, ch = self._canvas_w * S, self._canvas_h * S
        tk_rgb = tuple(int(self.TRANSPARENT_KEY[i:i + 2], 16) for i in (1, 3, 5))

        # ── 圆角蒙版（逻辑区域） ──
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, w - 1, h - 1], radius=r, fill=255)

        # ── 柔和投影 ──
        shadow_offset_y = int(self._SHADOW_OFFSET_Y * S)
        shadow_blur_r = int(self._SHADOW_BLUR * S)
        sr, sg, sb, sa = self.SHADOW_COLOR

        # 在画布大小上绘制阴影
        shadow_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        # 阴影形状（稍微偏下）
        sx0 = pad
        sy0 = pad + shadow_offset_y
        shadow_draw.rounded_rectangle(
            [sx0, sy0, sx0 + w - 1, sy0 + h - 1], radius=r,
            fill=(sr, sg, sb, sa))
        shadow_layer = shadow_layer.filter(
            ImageFilter.GaussianBlur(radius=shadow_blur_r))

        # ── 渐变底色（上→下，白→极浅暖灰） ──
        base = Image.new("RGBA", (w, h))
        bd = ImageDraw.Draw(base)
        r1, g1, b1 = self.BG_TOP
        r2, g2, b2 = self.BG_BOTTOM
        for yy in range(h):
            t_ = yy / max(1, h - 1)
            bd.line([(0, yy), (w, yy)], fill=(
                int(r1 + (r2 - r1) * t_),
                int(g1 + (g2 - g1) * t_),
                int(b1 + (b2 - b1) * t_), 255))

        # ── 噪点纹理层（磨砂质感，非常微妙） ──
        noise = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = noise.load()
        rng = random.Random(42)
        for ny in range(0, h, 2):
            for nx in range(0, w, 2):
                if rng.random() < 0.18:
                    # 混合黑白噪点，模拟真实磨砂
                    if rng.random() < 0.5:
                        v = rng.randint(230, 255)
                    else:
                        v = rng.randint(180, 210)
                    a = rng.randint(4, self.FROST_ALPHA)
                    c = (v, v, v, a)
                    px[nx, ny] = c
                    if nx + 1 < w:
                        px[nx + 1, ny] = c
                    if ny + 1 < h:
                        px[nx, ny + 1] = c

        frost = Image.alpha_composite(base, noise)

        # ── 顶部高光（非常微妙的白色渐隐，模拟光源） ──
        hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hl)
        band = int(h * 0.35)
        for hy in range(band):
            a = int(30 * (1 - hy / band) ** 2)
            hd.line([(r, hy), (w - r, hy)], fill=(255, 255, 255, a))
        frost = Image.alpha_composite(frost, hl)

        # ── 应用圆角蒙版 ──
        body = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        body.paste(frost, mask=mask)

        # ── 极细描边（几乎看不见，仅提示边界） ──
        br, bg_c, bb, ba = self.BORDER_COLOR
        edge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(edge).rounded_rectangle(
            [0, 0, w - 1, h - 1], radius=r,
            outline=(br, bg_c, bb, ba), width=max(1, S))
        body = Image.alpha_composite(body, edge)

        # ── 合成到画布（先阴影，再主体） ──
        canvas_img = Image.new("RGBA", (cw, ch), (*tk_rgb, 255))
        canvas_img = Image.alpha_composite(canvas_img, shadow_layer)
        canvas_img.paste(body, (pad, pad), mask=body)

        # ── 缩回 1x ──
        final_rgba = canvas_img.resize(
            (self._canvas_w, self._canvas_h), Image.LANCZOS)
        # 转 RGB，透明区域填 transparent key
        final = Image.new("RGB", (self._canvas_w, self._canvas_h), tk_rgb)
        final.paste(final_rgba, mask=final_rgba.split()[3])
        return ImageTk.PhotoImage(final)

    def _draw_bg(self):
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)

    # ════════════════ public API (线程安全) ════════════════

    def show_recording(self, recorder):
        self._recorder = recorder
        if self._root:
            self._root.after(0, self._do_show_recording)

    def show_recognizing(self):
        if self._root:
            self._root.after(0, self._do_show_recognizing)

    def show_result(self, text: str):
        if self._root:
            self._root.after(0, lambda: self._do_show_result(text))

    def hide(self):
        if self._root:
            self._root.after(0, self._do_hide)

    # ════════════════ internal ════════════════

    def _cancel_jobs(self):
        if self._anim_job is not None:
            self._root.after_cancel(self._anim_job)
            self._anim_job = None
        if self._hide_job is not None:
            self._root.after_cancel(self._hide_job)
            self._hide_job = None

    # ════════════════ adaptive gain ════════════════

    def _update_gain(self, raw_vol: float) -> float:
        """自适应增益：根据近期音量动态缩放，防止柱子过早触顶。

        返回归一化后的 0.0-1.0 音量值。
        """
        self._gain_history.append(raw_vol)

        # 计算滚动窗口的参考值（80th 百分位）
        if len(self._gain_history) >= 3:
            sorted_hist = sorted(self._gain_history)
            idx = int(len(sorted_hist) * self._GAIN_PERCENTILE)
            idx = min(idx, len(sorted_hist) - 1)
            target_ref = max(sorted_hist[idx], self._GAIN_MIN_REF)
        else:
            target_ref = max(raw_vol, self._GAIN_MIN_REF)

        # 平滑跟踪参考值：快升慢降
        if target_ref > self._gain_ref:
            # 快速上升，响应大音量
            self._gain_ref += (target_ref - self._gain_ref) * self._GAIN_RISE
        else:
            # 慢速衰减，保持稳定
            self._gain_ref = self._gain_ref * self._GAIN_DECAY + target_ref * (1.0 - self._GAIN_DECAY)

        # 确保参考值不低于最小阈值
        self._gain_ref = max(self._gain_ref, self._GAIN_MIN_REF)

        # 缩放：目标是正常说话大约 80% 高度
        scaled = raw_vol / (self._gain_ref * 1.25)
        return max(0.0, min(1.0, scaled))

    # ════════════════ waveform smoothing ════════════════

    def _smooth_bars(self, values: list[float]) -> list[float]:
        """相邻柱子互相影响，产生有机波浪形态而非锯齿状随机跳动。"""
        if len(values) <= 2:
            return values
        w = self._SMOOTH_WEIGHT
        smoothed = list(values)
        for i in range(len(values)):
            left = values[i - 1] if i > 0 else values[i]
            right = values[i + 1] if i < len(values) - 1 else values[i]
            # 加权平均：自身 (1-w) + 邻居均值 w
            smoothed[i] = values[i] * (1.0 - w) + (left + right) / 2.0 * w
        return smoothed

    # ── recording ──

    def _do_show_recording(self):
        self._cancel_jobs()
        self._state = "recording"
        self._vol_hist.clear()
        self._gain_history.clear()
        self._gain_ref = self._GAIN_MIN_REF
        self._root.deiconify()
        self._draw_bg()
        self._tick_recording()

    def _tick_recording(self):
        if self._state != "recording":
            return

        now = _time.time()
        cy = self._pad + self.H // 2
        s = self._s

        raw_vol = self._recorder.current_volume if self._recorder else 0.0
        scaled_vol = self._update_gain(raw_vol)
        self._vol_hist.append(scaled_vol)

        # ── 红色录音指示点（V3: 显著呼吸脉冲 — 大小 + 颜色） ──
        self._canvas.delete("ind")
        # 呼吸因子：宽范围 0.2 ~ 1.0，视觉上非常明显
        breath_raw = (math.sin(now * 2.5) + 1.0) / 2.0   # 0.0 ~ 1.0
        breath = 0.2 + 0.8 * breath_raw                    # 0.2 ~ 1.0

        # 脉冲尺寸：70% ~ 100% 半径
        dot_r_max = int(4.5 * s)
        dot_r = max(2, int(dot_r_max * (0.7 + 0.3 * breath_raw)))
        dot_color = _lerp_hex(self.REC_DOT_DIM, self.REC_DOT_COLOR, breath)

        # 柔和光晕（随呼吸变化）
        halo_r_max = int(8 * s)
        halo_r = max(3, int(halo_r_max * (0.75 + 0.25 * breath_raw)))
        halo_color = _lerp_hex("#FFFFFF", self.REC_DOT_COLOR, 0.25 + 0.25 * breath)
        self._canvas.create_oval(
            self._dot_cx - halo_r, cy - halo_r,
            self._dot_cx + halo_r, cy + halo_r,
            fill=halo_color, outline="", stipple="gray25", tags="ind")

        # 实心红点
        self._canvas.create_oval(
            self._dot_cx - dot_r, cy - dot_r,
            self._dot_cx + dot_r, cy + dot_r,
            fill=dot_color, outline="", tags="ind")

        # ── REC 标签 ──
        self._canvas.delete("lbl")
        self._canvas.create_text(
            self._label_x, cy, text="REC",
            fill=self.REC_LABEL_COLOR,
            font=self._font_label, anchor="w", tags="lbl")

        # ── 有机音量波形 ──
        self._canvas.delete("bars")
        max_h = self.H - int(14 * s)
        hist = list(self._vol_hist)
        offset = self._bar_n - len(hist)

        # 波形平滑：相邻柱子互相影响
        smoothed = self._smooth_bars(hist)

        for i, v in enumerate(smoothed):
            bi = offset + i
            x_center = self._bar_x0 + bi * self._bstep + self._bw // 2

            # 柱高（保证最小可见高度）
            min_h = int(2 * s)
            bh = max(min_h, int(v * max_h))

            # 高度比例用于颜色映射
            ratio = bh / max(1, max_h)

            # 四段渐变颜色映射：灰 → 暖灰粉 → 桃粉 → 珊瑚 → 红
            if ratio < 0.2:
                color = _lerp_hex(self.BAR_IDLE, self.BAR_LOW, ratio / 0.2)
            elif ratio < 0.45:
                color = _lerp_hex(self.BAR_LOW, self.BAR_MID, (ratio - 0.2) / 0.25)
            elif ratio < 0.75:
                color = _lerp_hex(self.BAR_MID, self.BAR_HIGH, (ratio - 0.45) / 0.3)
            else:
                color = _lerp_hex(self.BAR_HIGH, self.BAR_PEAK, (ratio - 0.75) / 0.25)

            # 柱顶高光色（比主色更亮）
            tip_color = _lerp_hex(color, self.BAR_TIP_GLOW, 0.35)

            y0 = cy - bh // 2
            y1 = cy + bh // 2

            # 锥形柱子：中间宽、两端窄（更有机的形态）
            # 使用多边形模拟锥形 + 圆帽
            half_w = self._bw / 2.0
            taper = 0.65  # 末端宽度 = 65% 的中间宽度

            if bh > int(4 * s):
                # 足够高的柱子：画锥形主体 + 圆帽 + 高光
                tip_half_w = half_w * taper
                mid_y_top = cy - bh // 4
                mid_y_bot = cy + bh // 4

                # 主体：梯形多边形（上窄-中宽-下窄）
                # 为了更圆润，我们分段画
                # 上半段：圆帽 + 锥形
                cap_r = max(1, int(tip_half_w))
                self._canvas.create_oval(
                    int(x_center - tip_half_w), y0,
                    int(x_center + tip_half_w), y0 + cap_r * 2,
                    fill=tip_color, outline="", tags="bars")
                # 中间矩形（最宽处）
                self._canvas.create_rectangle(
                    int(x_center - half_w), mid_y_top,
                    int(x_center + half_w), mid_y_bot,
                    fill=color, outline="", tags="bars")
                # 上锥形连接（帽到中间）
                self._canvas.create_polygon(
                    int(x_center - tip_half_w), y0 + cap_r,
                    int(x_center + tip_half_w), y0 + cap_r,
                    int(x_center + half_w), mid_y_top,
                    int(x_center - half_w), mid_y_top,
                    fill=color, outline="", tags="bars")
                # 下锥形连接（中间到帽）
                self._canvas.create_polygon(
                    int(x_center - half_w), mid_y_bot,
                    int(x_center + half_w), mid_y_bot,
                    int(x_center + tip_half_w), y1 - cap_r,
                    int(x_center - tip_half_w), y1 - cap_r,
                    fill=color, outline="", tags="bars")
                # 下圆帽
                self._canvas.create_oval(
                    int(x_center - tip_half_w), y1 - cap_r * 2,
                    int(x_center + tip_half_w), y1,
                    fill=color, outline="", tags="bars")

                # ── 倒影：中心线下方的淡影 ──
                refl_h = max(1, bh // 5)
                refl_y0 = y1 + int(1 * s)
                refl_y1 = refl_y0 + refl_h
                # 倒影用 stipple 模拟低透明度
                refl_color = _lerp_hex(color, "#F3F3F8", 0.7)  # 非常淡
                refl_half_w = tip_half_w * 0.8
                self._canvas.create_oval(
                    int(x_center - refl_half_w), refl_y0,
                    int(x_center + refl_half_w), refl_y1,
                    fill=refl_color, outline="", stipple="gray12", tags="bars")
            else:
                # 很短的柱子：简单椭圆
                self._canvas.create_oval(
                    int(x_center - half_w), y0,
                    int(x_center + half_w), y1,
                    fill=color, outline="", tags="bars")

        self._anim_job = self._root.after(50, self._tick_recording)

    # ── recognizing ──

    def _do_show_recognizing(self):
        self._cancel_jobs()
        self._state = "recognizing"
        self._recorder = None
        self._recog_step = 0
        self._root.deiconify()
        self._draw_bg()
        self._tick_recognizing()

    def _tick_recognizing(self):
        if self._state != "recognizing":
            return
        self._canvas.delete("recog")

        now = _time.time()
        cx = self._pad + self.W // 2
        cy = self._pad + self.H // 2
        s = self._s
        label = t("overlay.recognizing")

        # 文字
        self._canvas.create_text(
            cx - int(14 * s), cy, text=label, fill=self.RECOG_TEXT,
            font=self._font_text, anchor="center", tags="recog")

        # 三个脉冲圆点 — 依次明灭，macOS 风格
        dot_x0 = cx + int(20 * s)
        dot_spacing = int(8 * s)
        dot_base_r = int(2.5 * s)

        for i in range(3):
            # 平滑的序列脉冲：每个点有时间偏移
            phase = (math.sin(now * 2.8 - i * 0.9) + 1) / 2
            r_scale = 1.0 + 0.3 * phase
            dr = int(dot_base_r * r_scale)
            dx = dot_x0 + i * dot_spacing
            c = _lerp_hex(self.RECOG_DOT_DIM, self.RECOG_DOT_HI, phase)
            self._canvas.create_oval(
                dx - dr, cy - dr, dx + dr, cy + dr,
                fill=c, outline="", tags="recog")

        self._recog_step += 1
        self._anim_job = self._root.after(50, self._tick_recognizing)

    # ── result ──

    def _do_show_result(self, text: str):
        self._cancel_jobs()
        self._state = "result"
        self._root.deiconify()
        self._draw_bg()
        display = text if len(text) <= 28 else text[:25] + "..."
        cx = self._pad + self.W // 2
        cy = self._pad + self.H // 2
        self._canvas.create_text(
            cx, cy, text=display,
            fill=self.RESULT_TEXT, font=self._font_text, anchor="center")
        self._hide_job = self._root.after(2000, self._do_hide)

    # ── hide ──

    def _do_hide(self):
        self._cancel_jobs()
        self._state = "hidden"
        self._recorder = None
        self._root.withdraw()


# ════════════════ utils ════════════════

def _lerp_hex(a: str, b: str, t: float) -> str:
    """线性插值两个 hex 颜色。"""
    t = max(0.0, min(1.0, t))
    ra, ga, ba = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    rb, gb, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return f"#{int(ra+(rb-ra)*t):02x}{int(ga+(gb-ga)*t):02x}{int(ba+(bb-ba)*t):02x}"
