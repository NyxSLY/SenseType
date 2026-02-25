MODEL_ID = "iic/SenseVoiceSmall"     # ModelScope模型ID
DEVICE = "auto"                       # "auto"=自动检测 / "cuda:0" / "cpu"
LANGUAGE = "auto"                     # auto / zh / en
USE_ITN = True                        # 自动加标点和逆文本正则化
HOTKEY = "ctrl+alt+z"                 # 全局快捷键
MODE = "toggle"                       # "hold"=按住说话松开识别, "toggle"=按一下开始再按一下停止
SAMPLE_RATE = 16000                   # 录音采样率
VAD_MAX_SEGMENT_MS = 30000            # VAD最大分段时长
SILENCE_THRESHOLD = 0.01              # 静音判定阈值
PASTE_DELAY_MS = 80                   # 粘贴后恢复剪贴板的等待时间(ms)
AUDIO_SAVE_DIR = ""                   # 录音保存目录，空字符串则用默认路径 ~/sensetype_audio
AUDIO_KEEP_COUNT = 10                 # 保留最近几条录音，超出自动删除最旧的
OVERLAY_ENABLED = True                # 是否显示浮动状态条（False则纯后端运行）
