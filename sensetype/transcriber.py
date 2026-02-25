import io
import sys
import numpy as np
from .config import MODEL_ID, DEVICE, LANGUAGE, USE_ITN, VAD_MAX_SEGMENT_MS

MIN_VRAM_GB = 4  # 低于此值自动回退CPU（T400=2GB会OOM）


def _resolve_device(device_cfg: str) -> str:
    """根据配置和硬件情况决定实际使用的设备。"""
    if device_cfg != "auto":
        return device_cfg
    try:
        import torch
        if not torch.cuda.is_available():
            print("[设备] CUDA 不可用，使用 CPU")
            return "cpu"
        vram_gb = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
        name = torch.cuda.get_device_name(0)
        print(f"[设备] 检测到 GPU: {name}（显存 {vram_gb:.1f}GB）")
        if vram_gb < MIN_VRAM_GB:
            print(f"[设备] 显存 < {MIN_VRAM_GB}GB，回退 CPU（避免 OOM）")
            return "cpu"
        return "cuda:0"
    except Exception:
        print("[设备] GPU 检测失败，使用 CPU")
        return "cpu"


class Transcriber:
    def __init__(self):
        device = _resolve_device(DEVICE)
        print(f"[模型] 正在加载 {MODEL_ID}（设备: {device}，首次需下载~400MB）...")
        # 抑制 FunASR 的 "ffmpeg is not installed" 提示（项目传 numpy 数组，不需要 ffmpeg）
        _stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
            self._postprocess = rich_transcription_postprocess
            self.model = AutoModel(
                model=MODEL_ID,
                trust_remote_code=True,
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": VAD_MAX_SEGMENT_MS},
                device=device,
            )
        finally:
            sys.stderr = _stderr
        print(f"[模型] 加载完成（{device}）")

    def transcribe(self, audio: np.ndarray) -> str:
        res = self.model.generate(
            input=audio,
            cache={},
            language=LANGUAGE,
            use_itn=USE_ITN,
        )
        if not res or not res[0].get("text"):
            return ""
        raw_text = res[0]["text"]
        text = self._postprocess(raw_text)
        return text.strip()
