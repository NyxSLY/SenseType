import threading
from PIL import Image, ImageDraw, ImageFont
import pystray

from .i18n import t

# 状态常量
STATE_LOADING = "loading"
STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_RECOGNIZING = "recognizing"

# 状态对应的颜色
_COLORS = {
    STATE_LOADING: "#888888",     # 灰色 - 加载中
    STATE_IDLE: "#4CAF50",        # 绿色 - 就绪
    STATE_RECORDING: "#F44336",   # 红色 - 录音中
    STATE_RECOGNIZING: "#FF9800", # 橙色 - 识别中
}

# 状态 → i18n key
_LABEL_KEYS = {
    STATE_LOADING: "tray.loading",
    STATE_IDLE: "tray.idle",
    STATE_RECORDING: "tray.recording",
    STATE_RECOGNIZING: "tray.recognizing",
}


def _create_icon(color: str) -> Image.Image:
    """生成一个纯色圆形图标。"""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color)
    return img


class TrayIcon:
    def __init__(self, on_quit):
        self._on_quit = on_quit
        self._state = STATE_LOADING
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        """在后台线程启动托盘图标。"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: t("tray.status", label=t(_LABEL_KEYS.get(self._state, "tray.idle"))),
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.quit"), self._quit),
        )
        self._icon = pystray.Icon(
            name="SenseType",
            icon=_create_icon(_COLORS[self._state]),
            title=f"SenseType - {t(_LABEL_KEYS.get(self._state, 'tray.idle'))}",
            menu=menu,
        )
        self._icon.run()

    def set_state(self, state: str):
        """更新托盘图标状态。"""
        self._state = state
        if self._icon:
            self._icon.icon = _create_icon(_COLORS.get(state, "#888888"))
            self._icon.title = f"SenseType - {t(_LABEL_KEYS.get(state, 'tray.idle'))}"

    def _quit(self, icon, item):
        if self._icon:
            self._icon.stop()
        self._on_quit()

    def stop(self):
        if self._icon:
            self._icon.stop()
