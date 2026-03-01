"""i18n — 根据 Windows 系统语言切换中英文界面。"""

import locale

def _detect_lang() -> str:
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang.startswith("zh"):
            return "zh"
    except Exception:
        pass
    return "en"

LANG = _detect_lang()

_ZH = {
    # main.py
    "app.title": "=== SenseType 本地语音输入 ===",
    "app.hotkey_toggle": "快捷键: 按 {hotkey} 开始/停止录音（toggle模式）",
    "app.hotkey_hold": "快捷键: 按住 {hotkey} 说话，松开识别（hold模式）",
    "app.quit_hint": "退出方式: 右键托盘图标 → 退出，或关闭此窗口",
    "app.ready": "就绪，等待语音输入...",
    "app.exited": "已退出",
    "skip.silent": "[跳过] 音频过于安静",
    "recog.start": "[识别] 正在识别...",
    "recog.result": "[结果] {text}",
    "recog.empty": "[识别] 未识别到文字",
    # transcriber.py
    "device.no_cuda": "[设备] CUDA 不可用，使用 CPU",
    "device.gpu_found": "[设备] 检测到 GPU: {name}（显存 {vram}GB）",
    "device.low_vram": "[设备] 显存 < {min_gb}GB，回退 CPU（避免 OOM）",
    "device.gpu_fail": "[设备] GPU 检测失败（{error}），使用 CPU",
    "model.loading": "[模型] 正在加载 {model_id}（设备: {device}，首次需下载~400MB）...",
    "model.loaded": "[模型] 加载完成（{device}）",
    # recorder.py
    "rec.sd_status": "[录音] sounddevice状态: {status}",
    "rec.start": "[录音] 开始录音...",
    "rec.no_audio": "[录音] 未采集到音频",
    "rec.done": "[录音] 结束，时长 {duration}s",
    "rec.saved": "[录音] 已保存: {path}",
    "rec.save_fail": "[录音] 保存失败: {error}",
    # tray.py
    "tray.loading": "加载中...",
    "tray.idle": "就绪",
    "tray.recording": "录音中",
    "tray.recognizing": "识别中...",
    "tray.status": "状态: {label}",
    "tray.quit": "退出",
    # input_paste.py
    "paste.fail": "[粘贴] 写入剪贴板失败",
    # overlay.py
    "overlay.win32_fail": "[Overlay] Win32样式设置失败: {error}",
    "overlay.recognizing": "识别中",
}

_EN = {
    # main.py
    "app.title": "=== SenseType Local Voice Input ===",
    "app.hotkey_toggle": "Hotkey: press {hotkey} to start/stop recording (toggle mode)",
    "app.hotkey_hold": "Hotkey: hold {hotkey} to speak, release to recognize (hold mode)",
    "app.quit_hint": "Quit: right-click tray icon → Quit, or close this window",
    "app.ready": "Ready, waiting for voice input...",
    "app.exited": "Exited",
    "skip.silent": "[Skip] Audio too quiet",
    "recog.start": "[Recog] Recognizing...",
    "recog.result": "[Result] {text}",
    "recog.empty": "[Recog] No text recognized",
    # transcriber.py
    "device.no_cuda": "[Device] CUDA unavailable, using CPU",
    "device.gpu_found": "[Device] GPU detected: {name} (VRAM {vram}GB)",
    "device.low_vram": "[Device] VRAM < {min_gb}GB, falling back to CPU (avoid OOM)",
    "device.gpu_fail": "[Device] GPU detection failed ({error}), using CPU",
    "model.loading": "[Model] Loading {model_id} (device: {device}, first run downloads ~400MB)...",
    "model.loaded": "[Model] Loaded ({device})",
    # recorder.py
    "rec.sd_status": "[Rec] sounddevice status: {status}",
    "rec.start": "[Rec] Recording started...",
    "rec.no_audio": "[Rec] No audio captured",
    "rec.done": "[Rec] Done, duration {duration}s",
    "rec.saved": "[Rec] Saved: {path}",
    "rec.save_fail": "[Rec] Save failed: {error}",
    # tray.py
    "tray.loading": "Loading...",
    "tray.idle": "Ready",
    "tray.recording": "Recording",
    "tray.recognizing": "Recognizing...",
    "tray.status": "Status: {label}",
    "tray.quit": "Quit",
    # input_paste.py
    "paste.fail": "[Paste] Failed to write clipboard",
    # overlay.py
    "overlay.win32_fail": "[Overlay] Win32 style setup failed: {error}",
    "overlay.recognizing": "Recognizing",
}

_STRINGS = {"zh": _ZH, "en": _EN}


def t(key: str, **kwargs) -> str:
    """翻译函数。返回当前语言对应的字符串，支持 .format() 填充。"""
    s = _STRINGS.get(LANG, _EN).get(key) or _EN.get(key, key)
    return s.format(**kwargs) if kwargs else s
