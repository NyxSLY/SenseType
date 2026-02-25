import threading
import numpy as np
import keyboard

from .config import HOTKEY, SILENCE_THRESHOLD, MODE, OVERLAY_ENABLED
from .i18n import t
from .recorder import Recorder
from .transcriber import Transcriber
from .input_paste import paste_text
from .tray import TrayIcon, STATE_LOADING, STATE_IDLE, STATE_RECORDING, STATE_RECOGNIZING
if OVERLAY_ENABLED:
    from .overlay import Overlay


def _parse_hotkey(hotkey: str):
    """将 'ctrl+alt+z' 拆分为修饰键列表和触发键。"""
    parts = [p.strip().lower() for p in hotkey.split("+")]
    trigger = parts[-1]
    modifiers = parts[:-1]
    return modifiers, trigger


def _modifiers_active(modifiers: list[str]) -> bool:
    """检查所有修饰键是否被按住。"""
    for mod in modifiers:
        if not keyboard.is_pressed(mod):
            return False
    return True


def main():
    print(t("app.title"))
    if MODE == "toggle":
        print(t("app.hotkey_toggle", hotkey=HOTKEY))
    else:
        print(t("app.hotkey_hold", hotkey=HOTKEY))
    print(t("app.press_esc") + "\n")

    # 托盘图标（退出回调会触发 keyboard 的 Esc）
    tray = TrayIcon(on_quit=lambda: keyboard.press_and_release("esc"))
    tray.start()

    tray.set_state(STATE_LOADING)
    transcriber = Transcriber()
    recorder = Recorder()
    overlay = Overlay() if OVERLAY_ENABLED else None
    if overlay:
        overlay.start()
    is_recording = False
    modifiers, trigger = _parse_hotkey(HOTKEY)
    tray.set_state(STATE_IDLE)

    def on_recognize(audio: np.ndarray):
        if np.max(np.abs(audio)) < SILENCE_THRESHOLD:
            print(t("skip.silent"))
            tray.set_state(STATE_IDLE)
            if overlay:
                overlay.hide()
            return
        tray.set_state(STATE_RECOGNIZING)
        if overlay:
            overlay.show_recognizing()
        print(t("recog.start"))
        text = transcriber.transcribe(audio)
        if text:
            print(t("recog.result", text=text))
            paste_text(text)
            if overlay:
                overlay.show_result(text)
        else:
            print(t("recog.empty"))
            if overlay:
                overlay.hide()
        tray.set_state(STATE_IDLE)

    def _start_recording():
        nonlocal is_recording
        is_recording = True
        tray.set_state(STATE_RECORDING)
        if overlay:
            overlay.show_recording(recorder)
        recorder.start()

    def _stop_and_recognize():
        nonlocal is_recording
        is_recording = False
        audio = recorder.stop()
        if audio is not None:
            threading.Thread(target=on_recognize, args=(audio,), daemon=True).start()
        else:
            tray.set_state(STATE_IDLE)

    # --- toggle 模式：按一下开始，再按一下停止 ---
    if MODE == "toggle":
        def on_toggle(event):
            if modifiers and not _modifiers_active(modifiers):
                return
            if not is_recording:
                _start_recording()
            else:
                _stop_and_recognize()

        keyboard.on_press_key(trigger, on_toggle, suppress=False)

    # --- hold 模式：按住说话，松开识别 ---
    else:
        def on_trigger_down(event):
            if is_recording:
                return
            if modifiers and not _modifiers_active(modifiers):
                return
            _start_recording()

        def on_trigger_up(event):
            if not is_recording:
                return
            _stop_and_recognize()

        keyboard.on_press_key(trigger, on_trigger_down, suppress=False)
        keyboard.on_release_key(trigger, on_trigger_up, suppress=False)

    print(t("app.ready") + "\n")
    keyboard.wait("esc")
    if overlay:
        overlay.stop()
    tray.stop()
    print("\n" + t("app.exited"))


if __name__ == "__main__":
    main()
