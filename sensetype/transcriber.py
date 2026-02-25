import io
import sys
import numpy as np
from .config import MODEL_ID, DEVICE, LANGUAGE, USE_ITN, VAD_MAX_SEGMENT_MS
from .i18n import t

MIN_VRAM_GB = 4  # 低于此值自动回退CPU（T400=2GB会OOM）


def _resolve_device(device_cfg: str) -> str:
    """根据配置和硬件情况决定实际使用的设备。"""
    if device_cfg != "auto":
        return device_cfg
    try:
        import torch
        if not torch.cuda.is_available():
            print(t("device.no_cuda"))
            return "cpu"
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        name = torch.cuda.get_device_name(0)
        print(t("device.gpu_found", name=name, vram=f"{vram_gb:.1f}"))
        if vram_gb < MIN_VRAM_GB:
            print(t("device.low_vram", min_gb=MIN_VRAM_GB))
            return "cpu"
        return "cuda:0"
    except Exception as e:
        print(t("device.gpu_fail", error=e))
        return "cpu"


class Transcriber:
    def __init__(self):
        device = _resolve_device(DEVICE)
        print(t("model.loading", model_id=MODEL_ID, device=device))
        # 抑制 FunASR/ModelScope 的杂项日志（版本检查、remote code警告、ffmpeg提示）
        _stdout, _stderr = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
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
                disable_update=True,
            )
        finally:
            sys.stdout, sys.stderr = _stdout, _stderr
        print(t("model.loaded", device=device))

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
