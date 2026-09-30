"""
Audio preprocessing helpers for SoulCare.

Resample to 16 kHz mono float32 — the input format expected by
Whisper-Small (Qualcomm AI Hub) and Silero-VAD.
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("soulcare.audio")

TARGET_SR = 16000


def load_audio_16k(audio_bytes: bytes, filename: str = "audio.webm") -> tuple[np.ndarray, int]:
    """
    Decode arbitrary audio bytes → mono float32 @ 16 kHz.
    Tries soundfile/librosa; falls back to raw int16 interpretation.
    """
    suffix = Path(filename).suffix or ".webm"
    try:
        import librosa  # type: ignore

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            y, sr = librosa.load(tmp.name, sr=TARGET_SR, mono=True)
            return y.astype(np.float32), TARGET_SR
    except Exception as exc:  # noqa: BLE001
        logger.debug("librosa decode failed (%s); trying soundfile/raw.", exc)

    try:
        import soundfile as sf  # type: ignore

        data, sr = sf.read(io.BytesIO(audio_bytes), always_2d=False)
        y = np.asarray(data, dtype=np.float32)
        if y.ndim > 1:
            y = y.mean(axis=1)
        if sr != TARGET_SR:
            # Linear resample fallback without librosa
            duration = len(y) / float(sr)
            new_len = max(1, int(duration * TARGET_SR))
            x_old = np.linspace(0, 1, num=len(y), endpoint=False)
            x_new = np.linspace(0, 1, num=new_len, endpoint=False)
            y = np.interp(x_new, x_old, y).astype(np.float32)
        return y, TARGET_SR
    except Exception as exc:  # noqa: BLE001
        logger.debug("soundfile decode failed (%s); raw fallback.", exc)

    # Last resort: treat as int16 PCM
    if len(audio_bytes) < 2:
        return np.zeros(TARGET_SR, dtype=np.float32), TARGET_SR
    pcm = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    return pcm, TARGET_SR


def pcm16_bytes(y: np.ndarray) -> bytes:
    clipped = np.clip(y, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


def audio_stats(y: np.ndarray, sr: int = TARGET_SR) -> dict[str, Any]:
    if y.size == 0:
        return {"duration_s": 0.0, "rms": 0.0, "peak": 0.0}
    return {
        "duration_s": round(float(y.size / sr), 3),
        "rms": round(float(np.sqrt(np.mean(np.square(y)))), 5),
        "peak": round(float(np.max(np.abs(y))), 5),
    }
