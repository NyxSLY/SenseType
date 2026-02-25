import time
import ctypes
import threading
from ctypes import wintypes
from .config import PASTE_DELAY_MS
from .i18n import t

# --- Windows API 常量 ---
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56
VK_MENU = 0x12      # Alt
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 64 位指针类型声明
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]

_paste_lock = threading.Lock()


def _set_clipboard(text: str) -> bool:
    """用 Win32 API 写入剪贴板。"""
    if not user32.OpenClipboard(0):
        return False
    try:
        user32.EmptyClipboard()
        data = text.encode("utf-16-le") + b"\x00\x00"
        h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h:
            return False
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
        return True
    finally:
        user32.CloseClipboard()


def _release_modifiers():
    """释放所有可能还被按住的修饰键，防止干扰 Ctrl+V。"""
    for vk in [VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN]:
        if user32.GetAsyncKeyState(vk) & 0x8000:
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)


def _send_ctrl_v():
    """用 keybd_event 模拟 Ctrl+V。"""
    _release_modifiers()
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def paste_text(text: str):
    """将文字通过剪贴板粘贴到当前光标位置。"""
    with _paste_lock:
        ok = _set_clipboard(text)
        if not ok:
            print(t("paste.fail"))
            return
        time.sleep(0.05)
        _send_ctrl_v()
        # 等待粘贴完成后再让出锁，不恢复剪贴板
        # （恢复剪贴板会在 Ctrl+V 生效前清掉内容，导致粘贴失败）
        time.sleep(PASTE_DELAY_MS / 1000.0)
