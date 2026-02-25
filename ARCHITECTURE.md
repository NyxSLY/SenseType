# SenseType 架构说明

## 文件结构

```
sensetype/
├── __main__.py        # 入口
├── main.py            # 主循环：热键监听 + 串联各模块
├── config.py          # 所有可配置项
├── recorder.py        # 录音（sounddevice）
├── transcriber.py     # 语音识别（SenseVoice / FunASR）
├── input_paste.py     # 文字粘贴到光标（Win32 剪贴板 + Ctrl+V）
├── tray.py            # 系统托盘图标（pystray）
└── overlay.py         # 浮动状态条（tkinter）← 前端 UI
```

## 后端流水线

```
热键按下 → recorder.start()
热键松开 → recorder.stop() → audio
         → transcriber.transcribe(audio) → text
         → input_paste.paste_text(text)
```

后端完全独立，不依赖任何 UI。`config.py` 中 `OVERLAY_ENABLED = False` 即可纯后端运行。

## 前端 UI 状态机

前端（overlay.py）只做视觉反馈，不影响后端逻辑。整个 UI 只有 4 个状态：

```
  ┌─ show_recording(recorder) ──► 录音中：● REC + 音量柱形图
  │
  ├─ show_recognizing() ────────► 识别中：Recognizing...
  │
  ├─ show_result(text) ─────────► 显示结果文字，2秒后自动隐藏
  │
  └─ hide() ────────────────────► 隐藏
```

### 状态切换时机（在 main.py 中）

| 事件 | 调用 |
|------|------|
| 开始录音 | `overlay.show_recording(recorder)` |
| 音频过于安静（跳过） | `overlay.hide()` |
| 开始识别 | `overlay.show_recognizing()` |
| 识别成功 | `overlay.show_result(text)` |
| 识别失败（无文字） | `overlay.hide()` |

### 线程安全

overlay 的 tkinter 主循环运行在独立线程。所有公开方法内部通过 `root.after(0, ...)` 调度到 tkinter 线程，外部可以从任何线程安全调用。

## 如何替换 / 自定义前端 UI

只需编写一个新类，实现以下 4 个方法：

```python
class MyOverlay:
    def start(self):
        """启动 UI（可以在后台线程）"""

    def stop(self):
        """销毁 UI"""

    def show_recording(self, recorder):
        """显示录音状态。recorder.current_volume 返回 0.0-1.0 的实时音量。"""

    def show_recognizing(self):
        """显示识别中状态。"""

    def show_result(self, text: str):
        """显示识别结果，建议 2 秒后自动隐藏。"""

    def hide(self):
        """隐藏 UI。"""
```

然后在 `main.py` 中替换 import：

```python
# from .overlay import Overlay
from .my_overlay import MyOverlay as Overlay
```

### recorder.current_volume

`recorder.current_volume` 是一个 property，返回 `float`（0.0-1.0），基于当前音频 chunk 的 RMS 值，用 sqrt 映射以增强低音量段的视觉反馈。可用于驱动音量柱形图、波形等可视化效果。

## config.py 配置项速查

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `HOTKEY` | `ctrl+alt+z` | 全局快捷键 |
| `MODE` | `toggle` | `hold`=按住说话 / `toggle`=按一下开始再按一下停止 |
| `OVERLAY_ENABLED` | `True` | 浮动状态条开关 |
| `DEVICE` | `cuda:0` | 推理设备（`cuda:0` / `cpu`） |
| `LANGUAGE` | `auto` | 识别语言（`auto` / `zh` / `en`） |
| `SILENCE_THRESHOLD` | `0.01` | 静音判定阈值 |
| `PASTE_DELAY_MS` | `80` | 粘贴后等待时间(ms) |
| `AUDIO_SAVE_DIR` | `""` | 录音保存目录（空=默认） |
| `AUDIO_KEEP_COUNT` | `10` | 保留最近几条录音 |
