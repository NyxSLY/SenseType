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
    """获取系统 DPI 缩放倍率（96dpi → 1.0, 144dpi → 1.5）。"""
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0


class Overlay:
    """屏幕底部浮动状态条 — 冰蓝科技毛玻璃风格，可鼠标拖动。"""

    # 逻辑尺寸（96dpi 基准），比例约 5:1
    _BASE_W = 290
    _BASE_H = 44
    _BASE_R = 12
    _BASE_MARGIN = 80
    TRANSPARENT_KEY = "#010101"

    # 超采样倍率（越高越清晰，3× 是质量/性能平衡点）
    _SS = 3

    # ── 配色 ──
    BG_BASE = (8, 12, 28)
    BG_LIGHTER = (18, 28, 56)
    FROST_ALPHA = 35
    BORDER_GLOW = (0, 140, 220, 50)
    BORDER_EDGE = (0, 175, 255, 110)
    HIGHLIGHT_RGB = (150, 205, 255)

    REC_DOT = "#00E5FF"
    REC_RING_DIM = "#003848"
    REC_LABEL = "#00E5FF"
    BAR_LO = "#0A4A80"
    BAR_HI = "#00D4FF"
    RECOG_COLOR = "#7EB8FF"
    RECOG_DOT = "#00D4FF"
    RESULT_COLOR = "#E8F4FF"

    _BASE_BAR_W = 4
    _BASE_BAR_GAP = 3

    FONT_FAMILY = "Candara"
    FONT_FAMILY_BODY = "Candara"

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

        # DPI 缩放（缓存，避免每帧调 Win32 API）
        s = _dpi_scale()
        self._s = s
        self.W = int(self._BASE_W * s)
        self.H = int(self._BASE_H * s)
        self.R = int(self._BASE_R * s)
        self.MARGIN = int(self._BASE_MARGIN * s)

        # 字体（缩小 25% 匹配新高度）
        fl = max(7, int(8 * s))
        ft = max(8, int(9 * s))
        self._font_label = (self.FONT_FAMILY, fl)
        self._font_text = (self.FONT_FAMILY_BODY, ft)

        # 录音区布局（逻辑坐标 × s）
        self._dot_cx = int(18 * s)
        self._label_x = int(32 * s)

        # 音量柱参数
        bw = max(3, int(self._BASE_BAR_W * s))
        bg = max(2, int(self._BASE_BAR_GAP * s))
        self._bw = bw
        self._bstep = bw + bg

        # REC 区右端 + 3~4 个 bar 间距
        rec_end = int(58 * s)
        gap = self._bstep * 4
        self._bar_x0 = rec_end + gap
        self._bar_x1 = self.W - int(14 * s)
        self._bar_n = max(4, (self._bar_x1 - self._bar_x0) // self._bstep)

        # 时间线滚动
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
        self._root.attributes("-alpha", 0.93)
        self._root.config(bg=self.TRANSPARENT_KEY)
        self._root.attributes("-transparentcolor", self.TRANSPARENT_KEY)

        self._canvas = tk.Canvas(
            self._root, width=self.W, height=self.H,
            bg=self.TRANSPARENT_KEY, highlightthickness=0,
        )
        self._canvas.pack()

        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - self.W) // 2
        y = sh - self.H - self.MARGIN
        self._root.geometry(f"{self.W}x{self.H}+{x}+{y}")

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

    # ════════════════ 毛玻璃背景（3× 超采样）════════════════

    def _render_bg(self):
        S = self._SS
        w, h, r = self.W * S, self.H * S, self.R * S
        tk_rgb = tuple(int(self.TRANSPARENT_KEY[i:i + 2], 16) for i in (1, 3, 5))

        # 圆角蒙版
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)

        # 渐变底色（上→下 浅→深）
        base = Image.new("RGBA", (w, h))
        bd = ImageDraw.Draw(base)
        r1, g1, b1 = self.BG_LIGHTER
        r2, g2, b2 = self.BG_BASE
        for yy in range(h):
            t_ = yy / h
            bd.line([(0, yy), (w, yy)], fill=(
                int(r1 + (r2 - r1) * t_),
                int(g1 + (g2 - g1) * t_),
                int(b1 + (b2 - b1) * t_), 255))

        # 噪点磨砂层
        noise = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = noise.load()
        rng = random.Random(42)
        for ny in range(0, h, 2):
            for nx in range(0, w, 2):
                if rng.random() < 0.30:
                    v = rng.randint(180, 255)
                    a = rng.randint(5, self.FROST_ALPHA)
                    c = (v, v, v, a)
                    px[nx, ny] = c
                    if nx + 1 < w:
                        px[nx + 1, ny] = c
                    if ny + 1 < h:
                        px[nx, ny + 1] = c

        frost = Image.alpha_composite(base, noise)

        # 顶部高光弧
        hl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        hd = ImageDraw.Draw(hl)
        hr_, hg_, hb_ = self.HIGHLIGHT_RGB
        band = int(h * 0.30)
        for hy in range(band):
            a = int(20 * (1 - hy / band))
            hd.line([(r, hy), (w - r, hy)], fill=(hr_, hg_, hb_, a))
        frost = Image.alpha_composite(frost, hl)

        # 应用蒙版
        result = Image.new("RGBA", (w, h), (*tk_rgb, 255))
        result.paste(frost, mask=mask)

        # 外发光
        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(
            [1, 1, w - 2, h - 2], radius=r,
            outline=self.BORDER_GLOW, width=S * 2)
        glow = glow.filter(ImageFilter.GaussianBlur(radius=S * 2))
        result = Image.alpha_composite(result, glow)

        # 内边框
        edge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(edge).rounded_rectangle(
            [S, S, w - S - 1, h - S - 1], radius=r - S,
            outline=self.BORDER_EDGE, width=1)
        result = Image.alpha_composite(result, edge)

        # 转 RGB → LANCZOS 缩回 1×
        final = Image.new("RGB", (w, h), tk_rgb)
        final.paste(result, mask=result.split()[3])
        final = final.resize((self.W, self.H), Image.LANCZOS)
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
        cy = self.H // 2

        vol = self._recorder.current_volume if self._recorder else 0.0
        self._vol_hist.append(vol)

        # ── 脉冲光环 ──
        self._canvas.delete("ind")
        pulse = 0.3 + 0.7 * abs(math.sin(now * 3.0))
        rr = int(6 * self._s)
        cr = int(2.5 * self._s)
        ring_c = _lerp_hex(self.REC_RING_DIM, self.REC_DOT, pulse)
        self._canvas.create_oval(
            self._dot_cx - rr, cy - rr, self._dot_cx + rr, cy + rr,
            outline=ring_c, width=2, fill="", tags="ind")
        self._canvas.create_oval(
            self._dot_cx - cr, cy - cr, self._dot_cx + cr, cy + cr,
            fill=self.REC_DOT, outline="", tags="ind")

        # ── REC ──
        self._canvas.delete("lbl")
        self._canvas.create_text(
            self._label_x, cy, text="REC", fill=self.REC_LABEL,
            font=self._font_label, anchor="w", tags="lbl")

        # ── 音量时间线 ──
        self._canvas.delete("bars")
        max_h = self.H - int(16 * self._s)
        hist = list(self._vol_hist)
        offset = self._bar_n - len(hist)

        for i, v in enumerate(hist):
            bi = offset + i
            x = self._bar_x0 + bi * self._bstep
            bh = max(int(2 * self._s), int(v * max_h))
            color = _lerp_hex(self.BAR_LO, self.BAR_HI, bh / max(1, max_h))
            self._canvas.create_rectangle(
                x, cy - bh // 2, x + self._bw, cy + bh // 2,
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
        cx, cy = self.W // 2, self.H // 2
        s = self._s
        label = t("overlay.recognizing")

        self._canvas.create_text(
            cx - int(12 * s), cy, text=label, fill=self.RECOG_COLOR,
            font=self._font_text, anchor="center", tags="recog")

        dot_x0 = cx + int(22 * s)
        for i in range(3):
            phase = (math.sin(now * 3.0 - i * 0.8) + 1) / 2
            dr = int((2 + phase * 2) * s)
            dx = dot_x0 + int(i * 10 * s)
            c = _lerp_hex(self.REC_RING_DIM, self.RECOG_DOT, phase)
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
        self._canvas.create_text(
            self.W // 2, self.H // 2, text=display,
            fill=self.RESULT_COLOR, font=self._font_text, anchor="center")
        self._hide_job = self._root.after(2000, self._do_hide)

    # ── hide ──

    def _do_hide(self):
        self._cancel_jobs()
        self._state = "hidden"
        self._recorder = None
        self._root.withdraw()


# ════════════════ utils ════════════════

def _lerp_hex(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    ra, ga, ba = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    rb, gb, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return f"#{int(ra+(rb-ra)*t):02x}{int(ga+(gb-ga)*t):02x}{int(ba+(bb-ba)*t):02x}"
