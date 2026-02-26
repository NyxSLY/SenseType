# SenseType

**Local voice typing for Windows, powered by SenseVoice -- 15x faster than Whisper, with better Chinese accuracy.**

[中文](README.md)

<!-- TODO: Add demo GIF -->

## Why SenseType?

- **Type anywhere** -- press a hotkey, speak, and text appears at your cursor in *any* Windows application (browser, Word, VS Code, WeChat, etc.)
- **Simple and lightweight** -- a single Python package, no complex setup, no background services
- **Free and open source** -- no subscriptions, no API keys, no usage limits
- **Best-in-class Chinese** -- powered by [SenseVoice-Small](https://github.com/FunAudioLLM/SenseVoice), which achieves 15-20% lower error rate than Whisper on Chinese
- **Blazing fast** -- non-autoregressive architecture processes 10s of audio in ~70ms, 15x faster than Whisper-Large
- **Fully local** -- all processing happens on your machine, nothing is uploaded
- **Just works** -- auto-detects GPU/CPU, built-in punctuation and voice activity detection, no post-processing needed

### SenseType vs Whisper-based tools

| | SenseType | Whisper-based tools |
|---|---|---|
| **Model** | SenseVoice-Small (Alibaba) | Whisper / faster-whisper |
| **Architecture** | Non-autoregressive | Autoregressive |
| **Speed** | ~70ms for 10s audio | ~1s+ for 10s audio |
| **Chinese CER** | Lower (15-20% improvement) | Higher |
| **Punctuation** | Built-in (ITN) | Requires post-processing |
| **VAD** | Built-in (FSMN-VAD) | Separate setup needed |

Speed and accuracy numbers are from [SenseVoice's published benchmarks](https://github.com/FunAudioLLM/SenseVoice).

## Features

- **Two input modes**: hold-to-talk or toggle (press once to start, again to stop)
- **Auto GPU/CPU selection** -- detects VRAM (4GB threshold), falls back to CPU automatically
- **Chinese-first** -- optimized for Chinese and Chinese-English mixed input; also supports English, Japanese, Korean, Cantonese
- **Visual feedback** -- floating status bar with live volume meter, system tray icon
- **Modular design** -- overlay UI is optional and replaceable, backend runs independently
- **Zero native dependencies** -- clipboard and key simulation via Win32 API through ctypes, no pywin32 needed

## Quick Start

**1. Create environment and install PyTorch**

```bash
# Using micromamba (or conda/venv)
micromamba create -n sensetype python=3.11 -y
micromamba activate sensetype

# GPU (CUDA 12.1)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Or CPU only
pip install torch torchaudio
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Run**

Double-click a launcher script in the project root:

| File | Description |
|------|-------------|
| `SenseType.bat` | With console window, shows logs, good for debugging |
| `SenseType.vbs` | No console window, double-click and go, best for daily use |

Both auto-locate the Python environment and request administrator privileges.

Or run manually from the command line (requires administrator):

```bash
python -m sensetype
```

The model (~400MB) downloads automatically from ModelScope on first run.

## Configuration

Edit `sensetype/config.py`:

| Option | Default | Description |
|--------|---------|-------------|
| `HOTKEY` | `ctrl+alt+z` | Global hotkey combination |
| `MODE` | `toggle` | `hold` = hold-to-talk, `toggle` = press to start/stop |
| `DEVICE` | `auto` | `auto` / `cuda:0` / `cpu` |
| `LANGUAGE` | `auto` | `auto` / `zh` / `en` / `ja` / `ko` / `yue` |
| `USE_ITN` | `True` | Auto-punctuation and inverse text normalization |
| `OVERLAY_ENABLED` | `True` | Show floating status bar (`False` for headless mode) |
| `SILENCE_THRESHOLD` | `0.01` | Skip audio below this volume level |
| `PASTE_DELAY_MS` | `80` | Delay before restoring clipboard (ms) |
| `AUDIO_SAVE_DIR` | `""` | Save recordings to this directory (empty = `~/sensetype_audio`) |
| `AUDIO_KEEP_COUNT` | `10` | Number of recent recordings to keep |

## Architecture

```
Hotkey Press ──► Recorder ──► Transcriber ──► Paste to Cursor
  (keyboard)    (sounddevice)  (SenseVoice)    (Win32 API)
                    │               │
                    ▼               ▼
               Overlay UI      System Tray
               (tkinter)       (pystray)
```

The backend pipeline (hotkey -> record -> transcribe -> paste) is fully independent of the UI. Set `OVERLAY_ENABLED = False` to run without any visual feedback.

```
sensetype/
├── __main__.py      # Entry point
├── main.py          # Main loop: hotkey listener + orchestration
├── config.py        # All configuration options
├── recorder.py      # Audio recording (sounddevice, 16kHz mono)
├── transcriber.py   # SenseVoice inference via FunASR AutoModel
├── input_paste.py   # Win32 clipboard paste (ctypes, no pywin32)
├── tray.py          # System tray icon (pystray)
└── overlay.py       # Floating status bar with volume visualization (tkinter)
```

## Comparison with Alternatives

| Tool | Model | Local? | Relative Speed | Chinese Quality |
|------|-------|--------|----------------|-----------------|
| **SenseType** | SenseVoice-Small | Yes | ~15x faster than Whisper-Large | Best (lowest CER) |
| [whisper-writer](https://github.com/savbell/whisper-writer) | OpenAI Whisper API | No (cloud) | Depends on network | Good |
| [whisper-typing](https://github.com/foges/whisper-typing) | faster-whisper | Yes | ~3x faster than Whisper | Good |
| [Privox](https://github.com/nicholasgasior/privox) | Faster-Whisper + Llama 3 | Yes | Moderate | Good + LLM post-processing |
| [whisper-ptt-windows](https://github.com/iceychris/whisper-ptt-windows) | Whisper (offline) | Yes | Baseline | Good |
| [TalkType](https://github.com/nicholasgasior/talktype) | Whisper | Yes | Baseline | Good |

Note: "Chinese Quality" comparisons are based on SenseVoice's published CER benchmarks against Whisper-Large-v3. TalkType is Linux-only.

## Requirements

- Windows 10/11
- Python 3.11
- Microphone
- NVIDIA GPU with >= 4GB VRAM (recommended) or CPU
- Administrator privileges (for global hotkey capture)

## Roadmap

- [ ] Audio feedback (start/stop recording sounds)
- [ ] Custom text post-processing rules (terminology correction)
- [ ] Auto-start with Windows
- [ ] VRAM stability monitoring for long sessions
- [ ] Overlay UI improvements

## License

[MIT](LICENSE)

## Acknowledgements

- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) by Alibaba FunAudioLLM -- the ASR model
- [FunASR](https://github.com/modelscope/FunASR) -- the inference framework
