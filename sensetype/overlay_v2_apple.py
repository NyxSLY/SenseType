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
    REC_DOT_COLOR = "#E8433A"      # SF Symbols 红（录音）
    REC_DOT_DIM = "#F5A8A4"        # 淡红（呼吸暗态）
    REC_LABEL_COLOR = "#C4372F"    # 标签文字稍深

    # 音量柱 — 温暖柔和
    BAR_IDLE = "#D1D1D6"           # 静默态：系统灰
    BAR_ACTIVE = "#E8433A"         # 有声态：与录音指示同色系
    BAR_MID = "#F09E8C"            # 中间过渡：温暖桃粉

    # 识别中
    RECOG_TEXT = "#48484A"         # 深灰（systemGray2）
    RECOG_DOT_DIM = "#D1D1D6"     # 浅灰
    RECOG_DOT_HI = "#8E8E93"      # 中灰

    # 结果文字
    RESULT_TEXT = "#1C1C1E"        # 近黑（label color）

    # ── 音量柱尺寸 ──
    _BASE_BAR_W = 3                # 更细的柱子
    _BASE_BAR_GAP = 2.5            # 更密的间距

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

    # ── recording ──

    def _do_show_recording(self):
        self._cancel_jobs()
        self._state = "recording"
        self._vol_hist.clear()
        self._root.deiconify()
        self._draw_bg()
        self._tick_recording()

    def _tick_recording(self):
        if self._state != "recording":
            return

        now = _time.time()
        cy = self._pad + self.H // 2

        vol = self._recorder.current_volume if self._recorder else 0.0
        self._vol_hist.append(vol)

        # ── 红色录音指示点（Apple 风格，柔和脉冲） ──
        self._canvas.delete("ind")
        # 缓慢、柔和的呼吸效果（正弦，不突兀）
        breath = 0.6 + 0.4 * ((math.sin(now * 2.5) + 1) / 2)
        dot_r = int(4.5 * self._s)
        dot_color = _lerp_hex(self.REC_DOT_DIM, self.REC_DOT_COLOR, breath)

        # 柔和光晕（比 V1 克制很多）
        halo_r = int(7 * self._s)
        halo_alpha = 0.15 + 0.15 * breath
        halo_color = _lerp_hex("#FFFFFF", self.REC_DOT_COLOR, 0.3 + 0.2 * breath)
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

        # ── 音量时间线（细腻、圆角风格） ──
        self._canvas.delete("bars")
        max_h = self.H - int(16 * self._s)
        hist = list(self._vol_hist)
        offset = self._bar_n - len(hist)

        for i, v in enumerate(hist):
            bi = offset + i
            x = self._bar_x0 + bi * self._bstep
            bh = max(int(2 * self._s), int(v * max_h))
            # 颜色：静默灰 → 桃粉 → 红
            ratio = bh / max(1, max_h)
            if ratio < 0.4:
                color = _lerp_hex(self.BAR_IDLE, self.BAR_MID, ratio / 0.4)
            else:
                color = _lerp_hex(self.BAR_MID, self.BAR_ACTIVE,
                                  (ratio - 0.4) / 0.6)
            # 圆角柱子 — 用 round_rectangle 模拟
            # tkinter Canvas 不支持 round rect，用 oval + rect 近似
            y0 = cy - bh // 2
            y1 = cy + bh // 2
            rr = min(self._bw // 2, 2)  # 柱子小圆角
            if bh > rr * 2:
                self._canvas.create_oval(
                    x, y0, x + self._bw, y0 + rr * 2,
                    fill=color, outline="", tags="bars")
                self._canvas.create_oval(
                    x, y1 - rr * 2, x + self._bw, y1,
                    fill=color, outline="", tags="bars")
                self._canvas.create_rectangle(
                    x, y0 + rr, x + self._bw, y1 - rr,
                    fill=color, outline="", tags="bars")
            else:
                self._canvas.create_oval(
                    x, y0, x + self._bw, y1,
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
