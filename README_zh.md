# SenseType

**Windows 本地语音输入工具 — 按下快捷键说话，文字自动输入到光标位置。**

基于阿里 [SenseVoice-Small](https://github.com/FunAudioLLM/SenseVoice) 模型，完全本地推理，不走云端。

[English](README.md)

---

## 为什么选择 SenseType

- **在任意位置输入** — 按下快捷键说话，文字自动输入到**任意 Windows 应用**的光标位置（浏览器、Word、VS Code、微信……）
- **简单轻量** — 一个 Python 包，无需复杂配置，无后台服务
- **免费开源** — 无需订阅、无 API 密钥、无使用限制
- **中文效果出色** — 基于 [SenseVoice-Small](https://github.com/FunAudioLLM/SenseVoice)，中文字错率比 Whisper 低 15-20%
- **极速推理** — 非自回归架构，10 秒音频仅需约 70ms，比 Whisper-Large 快 15 倍
- **完全本地** — 所有处理在本机完成，不上传任何数据，保护隐私
- **开箱即用** — 自动检测 GPU/CPU，内置标点恢复和语音活动检测，无需额外配置

### SenseType vs 基于 Whisper 的工具

| | SenseType | Whisper 系工具 |
|---|---|---|
| **模型** | SenseVoice-Small（阿里） | Whisper / faster-whisper |
| **架构** | 非自回归 | 自回归 |
| **速度** | 10s 音频 ~70ms | 10s 音频 ~1s+ |
| **中文字错率** | 更低（改善 15-20%） | 较高 |
| **标点恢复** | 内置 (ITN) | 需额外处理 |
| **VAD** | 内置 (FSMN-VAD) | 需单独配置 |

性能数据来源于 [SenseVoice 官方基准测试](https://github.com/FunAudioLLM/SenseVoice)。

## 功能特性

- 两种模式：**按住说话**（hold）和 **按一下开始再按一下停止**（toggle）
- **自动 GPU/CPU 检测** — 有 GPU 且显存 >= 4GB 时用 CUDA，否则自动回退 CPU
- 中文为主，支持中英混合输入（也支持英语、日语、韩语、粤语）
- 浮动状态条：录音时显示实时音量，识别时显示动画，结果自动消失
- 系统托盘图标，显示当前状态
- 录音自动保存（可配置保留数量）
- 纯 Win32 API 剪贴板操作，无需 pywin32

<!-- TODO: 添加演示GIF -->

## 快速开始

**1. 创建环境并安装 PyTorch**

```powershell
micromamba create -n sensetype python=3.11 -y
micromamba activate sensetype
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

> 无 GPU 或显存不足？直接 `pip install torch torchaudio`，程序会自动使用 CPU 推理。

**2. 安装依赖**

```powershell
pip install -r requirements.txt
```

**3. 运行**

```powershell
python -m sensetype
```

> 需要以**管理员权限**运行（全局热键捕获需要）。首次启动会从 ModelScope 下载模型（约 400MB）。

详细部署步骤请参考 [Windows 部署指南](Windows平台部署指南.md)。

## 配置

所有配置项在 `sensetype/config.py` 中修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `HOTKEY` | `ctrl+alt+z` | 全局快捷键 |
| `MODE` | `toggle` | `hold` = 按住说话 / `toggle` = 按一下开始再按一下停止 |
| `DEVICE` | `auto` | `auto` = 自动检测 / `cuda:0` / `cpu` |
| `LANGUAGE` | `auto` | `auto` = 自动检测 / `zh` / `en` |
| `USE_ITN` | `True` | 自动加标点和逆文本正则化 |
| `OVERLAY_ENABLED` | `True` | 浮动状态条开关（`False` 则纯后端运行） |
| `SILENCE_THRESHOLD` | `0.01` | 静音判定阈值（低于此值自动跳过） |
| `AUDIO_KEEP_COUNT` | `10` | 保留最近几条录音，超出自动删除 |
| `PASTE_DELAY_MS` | `80` | 粘贴后恢复剪贴板的等待时间 (ms) |

## 架构

```
┌─────────────────────────────────────────────────┐
│                   主线程                         │
│  keyboard 全局热键监听                            │
│  按下 → start_recording()                        │
│  松开 → stop_recording() → 启动识别线程           │
└─────────────────────────────────────────────────┘
         │                           │
         ▼                           ▼
┌─────────────────┐      ┌──────────────────────┐
│   录音线程        │      │   识别线程（异步）     │
│ sounddevice      │      │ SenseVoice 推理       │
│ 16kHz mono       │      │ → 后处理 + 标点恢复    │
│ float32          │      │ → 剪贴板粘贴到光标     │
└─────────────────┘      └──────────────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────────┐
│   系统托盘        │      │   浮动状态条           │
│ pystray          │      │ tkinter              │
│ 状态图标+右键菜单 │      │ 录音/识别/结果 可视化  │
└─────────────────┘      └──────────────────────┘
```

```
sensetype/
├── __main__.py      # 入口
├── main.py          # 主循环：热键监听 + 串联各模块
├── config.py        # 所有可配置项
├── recorder.py      # 录音（sounddevice）
├── transcriber.py   # 语音识别（SenseVoice / FunASR）
├── input_paste.py   # 文字粘贴（Win32 剪贴板 + Ctrl+V）
├── tray.py          # 系统托盘图标（pystray）
└── overlay.py       # 浮动状态条（tkinter）
```

## 与竞品对比

| 工具 | ASR 模型 | 本地推理 | 中文质量 | 速度 (10s 音频) | 平台 |
|------|----------|:--------:|----------|-----------------|------|
| **SenseType** | SenseVoice-Small | ✅ | 优秀 | ~70ms | Windows |
| [buzz](https://github.com/chidiwilliams/buzz) | Whisper | ✅ | 一般 | ~1s | 跨平台 |
| [WhisperWriter](https://github.com/savbell/whisper-writer) | Whisper | ✅ | 一般 | ~1s | Windows |
| 讯飞语音输入 | 讯飞引擎 | ❌ 云端 | 优秀 | 取决于网络 | Windows |
| 微软语音输入 (Win+H) | Azure Speech | ❌ 云端 | 良好 | 取决于网络 | Windows |

## 路线图

- [x] 全局快捷键录音（hold / toggle 两种模式）
- [x] SenseVoice 本地推理 + VAD + ITN
- [x] 剪贴板粘贴到任意应用光标位置
- [x] 浮动状态条（录音音量 + 识别动画）
- [x] 系统托盘图标
- [x] 自动 GPU/CPU 检测
- [ ] 录音开始/结束提示音
- [ ] 文本后处理规则（专业术语矫正）
- [ ] 开机自启
- [ ] 前端 UI 美化（pywebview 替代 tkinter）

## 技术栈

| 组件 | 技术 |
|------|------|
| 语音识别 | [SenseVoice-Small](https://github.com/FunAudioLLM/SenseVoice) via [FunASR](https://github.com/modelscope/FunASR) |
| 录音 | sounddevice（基于 PortAudio） |
| 热键 | keyboard |
| 浮动状态条 | tkinter + Pillow |
| 系统托盘 | pystray |
| 剪贴板/按键 | Win32 API（ctypes 直调） |

## 许可证

[MIT](LICENSE)
