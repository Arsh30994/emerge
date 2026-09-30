"""
Voice Activity Detection — Silero-VAD (~2MB, real-time).

Trims silence before Whisper-Small so Snapdragon NPU cycles
aren't wasted on empty frames.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np

from utils.audio_preprocessing import TARGET_SR, audio_stats, load_audio_16k

logger = logging.getLogger("soulcare.vad")


class VoiceActivityDetector:
    """Silero-VAD wrapper with energy-based demo fallback."""

    def __init__(self) -> None:
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.backend = "demo-energy"
        self._model = None
        self._get_speech_timestamps = None
        if os.getenv("FORCE_VAD", "0") == "1" or not self.demo_mode:
            self._try_load()

    def _try_load(self) -> None:
        try:
            import torch  # type: ignore

            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
            )
            self._model = model
            self._get_speech_timestamps = utils[0]
            self.backend = "silero-vad"
            self.demo_mode = False
            logger.info("Loaded Silero-VAD")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Silero-VAD unavailable (%s); energy VAD fallback.", exc)
            self.demo_mode = True
            self.backend = "demo-energy"

    def detect(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict[str, Any]:
        y, sr = load_audio_16k(audio_bytes, filename)
        stats = audio_stats(y, sr)

        if self._model is not None and self._get_speech_timestamps is not None:
            try:
                import torch  # type: ignore

                tensor = torch.from_numpy(y)
                stamps = self._get_speech_timestamps(tensor, self._model, sampling_rate=sr)
                segments = [
                    {
                        "start_s": round(s["start"] / sr, 3),
                        "end_s": round(s["end"] / sr, 3),
                    }
                    for s in stamps
                ]
                if stamps:
                    pieces = [y[s["start"] : s["end"]] for s in stamps]
                    trimmed = np.concatenate(pieces) if pieces else y
                else:
                    trimmed = y
                speech_ratio = float(trimmed.size / max(1, y.size))
                return {
                    "has_speech": len(segments) > 0,
                    "segments": segments,
                    "speech_ratio": round(speech_ratio, 3),
                    "trimmed_duration_s": round(float(trimmed.size / sr), 3),
                    "stats": stats,
                    "backend": self.backend,
                    "demo": False,
                    "waveform_preview": _downsample_preview(y),
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Silero inference failed (%s); energy fallback.", exc)

        return self._energy_vad(y, sr, stats)

    def _energy_vad(self, y: np.ndarray, sr: int, stats: dict[str, Any]) -> dict[str, Any]:
        if y.size == 0:
            return {
                "has_speech": False,
                "segments": [],
                "speech_ratio": 0.0,
                "trimmed_duration_s": 0.0,
                "stats": stats,
                "backend": self.backend,
                "demo": True,
                "waveform_preview": [],
            }
        frame = max(1, int(0.03 * sr))
        hop = frame
        energies = []
        for i in range(0, len(y) - frame, hop):
            energies.append(float(np.sqrt(np.mean(np.square(y[i : i + frame])))) )
        thr = max(0.01, float(np.median(energies)) * 1.5) if energies else 0.01
        speech_frames = [e >= thr for e in energies]
        segments = []
        start = None
        for idx, flagged in enumerate(speech_frames):
            if flagged and start is None:
                start = idx
            if not flagged and start is not None:
                segments.append(
                    {
                        "start_s": round(start * hop / sr, 3),
                        "end_s": round(idx * hop / sr, 3),
                    }
                )
                start = None
        if start is not None:
            segments.append(
                {
                    "start_s": round(start * hop / sr, 3),
                    "end_s": round(len(speech_frames) * hop / sr, 3),
                }
            )
        ratio = sum(speech_frames) / max(1, len(speech_frames))
        return {
            "has_speech": ratio > 0.05 or stats.get("rms", 0) > 0.005,
            "segments": segments,
            "speech_ratio": round(float(ratio), 3),
            "trimmed_duration_s": round(float(ratio * stats.get("duration_s", 0)), 3),
            "stats": stats,
            "backend": self.backend,
            "demo": True,
            "waveform_preview": _downsample_preview(y),
        }


def _downsample_preview(y: np.ndarray, points: int = 48) -> list[float]:
    if y.size == 0:
        return [0.0] * points
    idx = np.linspace(0, y.size - 1, num=points).astype(int)
    return [round(float(abs(v)), 4) for v in y[idx]]
