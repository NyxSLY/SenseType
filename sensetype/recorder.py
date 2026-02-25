import os
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from .config import SAMPLE_RATE, AUDIO_SAVE_DIR, AUDIO_KEEP_COUNT


def _cleanup_old_files(save_dir: Path):
    """只保留最近 AUDIO_KEEP_COUNT 条录音，删除最旧的。"""
    wav_files = sorted(save_dir.glob("*.wav"))
    to_delete = wav_files[:-AUDIO_KEEP_COUNT] if len(wav_files) > AUDIO_KEEP_COUNT else []
    for f in to_delete:
        try:
            f.unlink()
        except Exception:
            pass


def _get_save_dir() -> Path:
    if AUDIO_SAVE_DIR:
        d = Path(AUDIO_SAVE_DIR)
    else:
        d = Path.home() / "sensetype_audio"
    d.mkdir(parents=True, exist_ok=True)
    return d


class Recorder:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._recording = False
        self._current_rms: float = 0.0
        self.last_saved_path: str | None = None

    @property
    def current_volume(self) -> float:
        """当前音量，归一化到 0.0-1.0（供 overlay 读取）。"""
        # sqrt 映射：让低音量段也有明显的视觉反馈
        # RMS 0.01 → 0.4, RMS 0.05 → 0.89, RMS 0.08 → 1.0
        return min(1.0, self._current_rms ** 0.5 * 4)

    def _callback(self, indata: np.ndarray, frames, time_info, status):
        if status:
            print(f"[录音] sounddevice状态: {status}")
        with self._lock:
            if self._recording:
                self._chunks.append(indata.copy())
                self._current_rms = float(np.sqrt(np.mean(indata ** 2)))

    def start(self):
        with self._lock:
            self._chunks.clear()
            self._recording = True
            self._current_rms = 0.0
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()
        print("[录音] 开始录音...")

    def stop(self) -> np.ndarray | None:
        with self._lock:
            self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._chunks:
                print("[录音] 未采集到音频")
                return None
            audio = np.concatenate(self._chunks, axis=0).flatten()
            self._chunks.clear()
        duration = len(audio) / self.sample_rate
        print(f"[录音] 结束，时长 {duration:.1f}s")

        # 保存录音到文件
        try:
            save_dir = _get_save_dir()
            filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".wav"
            path = save_dir / filename
            sf.write(str(path), audio, self.sample_rate)
            self.last_saved_path = str(path)
            print(f"[录音] 已保存: {path}")
            _cleanup_old_files(save_dir)
        except Exception as e:
            print(f"[录音] 保存失败: {e}")

        return audio
