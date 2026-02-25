import tkinter as tk
import ctypes
import threading
import math
import time as _time

from PIL import Image, ImageDraw, ImageTk

from .i18n import t

# 高 DPI 感知 — 必须在创建任何窗口前调用，否则 tkinter 按 96DPI 渲染后被系统放大导致模糊
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
except Exception:
    pass


class Overlay:
    """屏幕底部浮动状态条 — 现代毛玻璃风格。"""

    WIDTH = 420
    HEIGHT = 52
    CORNER_R = 20
    BOTTOM_MARGIN = 80
    TRANSPARENT_KEY = "#010101"  # 接近黑色，与深色背景混合时边缘无瑕疵

    # ── 配色 ──
    BG_RGB = (18, 18, 32)       # 深蓝灰底
    BORDER_RGB = (55, 55, 80)   # 微亮边框
    REC_DOT = "#FF4757"         # 录音红点
    REC_LABEL = "#FF6B81"       # REC 文字（柔粉）
    BAR_HI = "#FF4757"          # 音量柱·高
    BAR_LO = "#FF8A9A"          # 音量柱·低
    RECOG_COLOR = "#FFB86C"     # 识别中（暖橙）
    RESULT_COLOR = "#E2E2E2"    # 结果文字（柔白）

    BAR_COUNT = 28
    BAR_WIDTH = 5

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

    # ════════════════ lifecycle ════════════════

    def start(self):
        """在后台线程启动 tkinter 事件循环。"""
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
        self._root.attributes("-alpha", 0.92)
        self._root.config(bg=self.TRANSPARENT_KEY)
        self._root.attributes("-transparentcolor", self.TRANSPARENT_KEY)

        self._canvas = tk.Canvas(
            self._root,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg=self.TRANSPARENT_KEY,
            highlightthickness=0,
        )
        self._canvas.pack()

        # 屏幕底部居中
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - self.WIDTH) // 2
        y = sh - self.HEIGHT - self.BOTTOM_MARGIN
        self._root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

        self._apply_win32_styles()
        self._bg_photo = self._render_bg()

        self._ready.set()
        self._root.mainloop()

    def _apply_win32_styles(self):
        try:
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_NOACTIVATE = 0x08000000

            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self._root.winfo_id())
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print(t("overlay.win32_fail", error=e))

    # ════════════════ 背景渲染 ════════════════

    def _render_bg(self):
        """PIL 2× 超采样绘制抗锯齿圆角背景 + 细边框。"""
        S = 2
        w, h, r = self.WIDTH * S, self.HEIGHT * S, self.CORNER_R * S
        tk_rgb = tuple(int(self.TRANSPARENT_KEY[i:i + 2], 16) for i in (1, 3, 5))

        img = Image.new("RGB", (w, h), tk_rgb)
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=self.BG_RGB)
        draw.rounded_rectangle([1, 1, w - 2, h - 2], radius=r - 1,
                               outline=self.BORDER_RGB, width=2)

        img = img.resize((self.WIDTH, self.HEIGHT), Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _draw_bg(self):
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)

    # ════════════════ public API (线程安全) ════════════════

    def show_recording(self, recorder):
        """显示录音状态，带音量柱形图动画。"""
        self._recorder = recorder
        if self._root:
            self._root.after(0, self._do_show_recording)

    def show_recognizing(self):
        """显示 Recognizing... 动画。"""
        if self._root:
            self._root.after(0, self._do_show_recognizing)

    def show_result(self, text: str):
        """显示识别结果，2 秒后自动隐藏。"""
        if self._root:
            self._root.after(0, lambda: self._do_show_result(text))

    def hide(self):
        """立即隐藏浮动条。"""
        if self._root:
            self._root.after(0, self._do_hide)

    # ════════════════ internal (tkinter 线程) ════════════════

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
        self._root.deiconify()
        self._draw_bg()
        self._canvas.create_text(
            56, self.HEIGHT // 2,
            text="REC",
            fill=self.REC_LABEL,
            font=("Segoe UI Semibold", 11),
            anchor="center",
        )
        self._tick_recording()

    def _tick_recording(self):
        if self._state != "recording":
            return

        t = _time.time()

        # 闪烁红点（0.5s 周期）
        self._canvas.delete("dot")
        if int(t * 2) % 2 == 0:
            cx, cy, radius = 28, self.HEIGHT // 2, 5
            self._canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                fill=self.REC_DOT, outline="", tags="dot",
            )

        # 音量柱形图
        vol = self._recorder.current_volume if self._recorder else 0.0
        self._canvas.delete("bars")
        area_x = 84
        area_end = self.WIDTH - 18
        step = (area_end - area_x) / self.BAR_COUNT

        for i in range(self.BAR_COUNT):
            x = area_x + i * step
            wave = 0.3 + 0.7 * abs(math.sin(t * 8 + i * 0.55))
            h = max(3, int(vol * wave * (self.HEIGHT - 20)))
            cy = self.HEIGHT // 2
            ratio = h / max(1, self.HEIGHT - 20)
            color = _lerp_hex(self.BAR_LO, self.BAR_HI, ratio)
            self._canvas.create_rectangle(
                x, cy - h // 2, x + self.BAR_WIDTH, cy + h // 2,
                fill=color, outline="", tags="bars",
            )

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
        dots = "." * (self._recog_step % 4)
        self._canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2,
            text=f"{t('overlay.recognizing')}{dots}",
            fill=self.RECOG_COLOR,
            font=("Segoe UI Semibold", 12),
            anchor="center",
            tags="recog",
        )
        self._recog_step += 1
        self._anim_job = self._root.after(400, self._tick_recognizing)

    # ── result ──

    def _do_show_result(self, text: str):
        self._cancel_jobs()
        self._state = "result"
        self._root.deiconify()
        self._draw_bg()
        display = text if len(text) <= 40 else text[:37] + "..."
        self._canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2,
            text=display,
            fill=self.RESULT_COLOR,
            font=("Segoe UI", 12),
            anchor="center",
        )
        self._hide_job = self._root.after(2000, self._do_hide)

    # ── hide ──

    def _do_hide(self):
        self._cancel_jobs()
        self._state = "hidden"
        self._recorder = None
        self._root.withdraw()


# ════════════════ utils ════════════════

def _lerp_hex(hex_a: str, hex_b: str, t: float) -> str:
    """线性插值两个 hex 颜色，t ∈ [0,1]。"""
    t = max(0.0, min(1.0, t))
    ra, ga, ba = int(hex_a[1:3], 16), int(hex_a[3:5], 16), int(hex_a[5:7], 16)
    rb, gb, bb = int(hex_b[1:3], 16), int(hex_b[3:5], 16), int(hex_b[5:7], 16)
    r = int(ra + (rb - ra) * t)
    g = int(ga + (gb - ga) * t)
    b = int(ba + (bb - ba) * t)
    return f"#{r:02x}{g:02x}{b:02x}"
