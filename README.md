# SenseType

**Windows 本地语音输入工具 — 按下快捷键说话，文字自动输入到任意应用的光标位置。**

免费、开源、完全离线、中文效果好。

[English](README_en.md)

<!-- TODO: 添加演示GIF -->

## 为什么用 SenseType

Windows 自带的语音输入（Win+H）需要联网，且中文效果一般。讯飞等商业工具要登录、要付费、要上传数据。GitHub 上现有的开源方案几乎都用 Whisper，中文不是强项。

SenseType 解决这些问题：

- **在任意位置输入** — 浏览器、Word、VS Code、微信、记事本……光标在哪，就输到哪
- **专为 Windows 设计** — Win32 API 直接调用，不依赖额外系统组件
- **免费开源** — 无订阅、无 API 密钥、无使用次数限制
- **完全本地** — 所有处理在本机完成，不上传任何音频数据
- **中文效果好** — 基于阿里 [SenseVoice-Small](https://github.com/FunAudioLLM/SenseVoice)，中文字错率比 Whisper 低 15-20%
- **速度快** — 非自回归架构，10 秒音频推理约 70ms，比 Whisper-Large 快 15 倍
- **开箱即用** — 自动检测 GPU/CPU、内置标点恢复和语音活动检测，无需额外配置
- **部署指南详细** — 从零开始的 [Windows 安装指南](docs/installation.md)，含清华源配置，小白也能跟着装

## 功能

- 全局快捷键 `Ctrl+Alt+Z`，在任意应用中触发
- 两种模式：**按住说话**（hold）/ **按一下开始再按一下停止**（toggle）
- 中文为主，支持中英混合输入（也支持英语、日语、韩语、粤语）
- 自动 GPU/CPU 检测 — 有显存 >= 4GB 的 GPU 用 CUDA，否则自动回退 CPU
- 浮动状态条 — 录音时显示实时音量，识别时显示动画
- 系统托盘图标 — 显示当前状态（加载中/就绪/录音/识别）
- 自动标点恢复（ITN） — 不用手动加逗号句号
- 录音自动保存 — 可配置保留数量

## 快速开始

> 完整的从零安装步骤（含 micromamba 安装、清华源配置、避坑指南），请看 **[Windows 安装指南](docs/installation.md)**。
>
> 以下是已有 Python 环境的快速安装方式。

**1. 创建环境 + 安装 PyTorch**

```powershell
micromamba create -n sensetype python=3.11 -y
micromamba activate sensetype

# 有 GPU（CUDA 12.1）
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# 无 GPU
pip install torch torchaudio
```

**2. 安装依赖**

```powershell
pip install -r requirements.txt
```

**3. 运行**

双击项目根目录的启动脚本即可：

| 文件 | 说明 |
|------|------|
| `SenseType.bat` | 带控制台窗口，可看运行日志，适合调试 |
| `SenseType.vbs` | 无控制台窗口，双击即用，适合日常使用 |

两者都会自动定位 Python 环境并以管理员权限运行。

也可以手动从命令行启动（需管理员权限）：

```powershell
python -m sensetype
```

首次启动会从 ModelScope 下载模型（约 400MB）。

## 配置

修改 `sensetype/config.py`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `HOTKEY` | `ctrl+alt+z` | 全局快捷键 |
| `MODE` | `toggle` | `hold` = 按住说话 / `toggle` = 按一下开始再按一下停止 |
| `DEVICE` | `auto` | `auto` = 自动检测 / `cuda:0` / `cpu` |
| `LANGUAGE` | `auto` | `auto` / `zh` / `en` / `ja` / `ko` / `yue` |
| `USE_ITN` | `True` | 自动加标点 |
| `OVERLAY_ENABLED` | `True` | 浮动状态条开关 |
| `SILENCE_THRESHOLD` | `0.01` | 静音判定阈值 |
| `AUDIO_KEEP_COUNT` | `10` | 保留最近几条录音 |

## 系统要求

- Windows 10/11
- Python 3.11
- 麦克风
- NVIDIA GPU（显存 >= 4GB，推荐）或 CPU
- 管理员权限（全局热键需要）

## 与竞品对比

| 工具 | 模型 | 本地 | 中文质量 | 速度 | 免费 |
|------|------|:----:|----------|------|:----:|
| **SenseType** | SenseVoice-Small | ✅ | 优秀 | ~70ms/10s | ✅ |
| Windows 语音输入 (Win+H) | Azure Speech | ❌ | 一般 | 取决于网络 | ✅ |
| 讯飞语音输入 | 讯飞引擎 | ❌ | 优秀 | 取决于网络 | 部分 |
| [buzz](https://github.com/chidiwilliams/buzz) | Whisper | ✅ | 一般 | ~1s/10s | ✅ |
| [WhisperWriter](https://github.com/savbell/whisper-writer) | Whisper | ✅ | 一般 | ~1s/10s | ✅ |

### SenseType vs Whisper

| | SenseType | Whisper 系工具 |
|---|---|---|
| **模型** | SenseVoice-Small（阿里） | Whisper / faster-whisper |
| **架构** | 非自回归 | 自回归 |
| **速度** | 10s 音频 ~70ms | 10s 音频 ~1s+ |
| **中文字错率** | 更低（改善 15-20%） | 较高 |
| **标点恢复** | 内置 | 需额外处理 |
| **语音活动检测** | 内置 (FSMN-VAD) | 需单独配置 |

性能数据来源于 [SenseVoice 官方基准测试](https://github.com/FunAudioLLM/SenseVoice)。

## 架构

```
快捷键按下 ──► 录音 ──► SenseVoice 识别 ──► 粘贴到光标
(keyboard)   (sounddevice)  (FunASR)      (Win32 API)
                 │                │
                 ▼                ▼
            浮动状态条         系统托盘
            (tkinter)         (pystray)
```

```
sensetype/
├── __main__.py      # 入口
├── main.py          # 主循环：热键监听 + 串联各模块
├── config.py        # 所有可配置项
├── recorder.py      # 录音（sounddevice, 16kHz mono）
├── transcriber.py   # 语音识别（SenseVoice via FunASR）
├── input_paste.py   # 粘贴到光标（Win32 剪贴板 + Ctrl+V）
├── tray.py          # 系统托盘图标
└── overlay.py       # 浮动状态条（音量可视化）
```

## 路线图

- [x] 全局快捷键录音（hold / toggle）
- [x] SenseVoice 本地推理 + VAD + ITN
- [x] 粘贴到任意应用光标位置
- [x] 浮动状态条 + 系统托盘
- [x] 自动 GPU/CPU 检测
- [ ] 录音开始/结束提示音
- [ ] 文本后处理规则（专业术语矫正）
- [ ] 开机自启
- [ ] 前端 UI 美化

## 许可证

[MIT](LICENSE)

## 致谢

- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) — 阿里 FunAudioLLM 团队的语音识别模型
- [FunASR](https://github.com/modelscope/FunASR) — 语音识别推理框架
