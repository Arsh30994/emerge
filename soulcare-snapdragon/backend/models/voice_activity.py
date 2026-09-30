"""
Voice Activity Detection — Silero-VAD via Qualcomm AI Hub.

Primary API (Snapdragon / AI Hub):
    from qai_hub_models.models.silero_vad import App
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from utils.audio_preprocessing import audio_stats, load_audio_16k

logger = logging.getLogger("soulcare.vad")


class SileroVAD:
    """Silero-VAD speech gate with energy-based demo fallback."""

    def __init__(self) -> None:
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.backend = "demo-energy"
        self.model: Any = None
        self._torch_vad = None
        self._get_speech_timestamps = None
        self._try_load()

    def _try_load(self) -> None:
        force = os.getenv("FORCE_VAD", "0") == "1"
        if self.demo_mode and not force:
            logger.info("SileroVAD demo mode (set FORCE_VAD=1 for AI Hub / Silero).")
            return

        # Qualcomm AI Hub path from hackathon brief
        try:
            from qai_hub_models.models.silero_vad import App  # type: ignore

            self.model = App()
            self.backend = "qai-hub-silero-vad"
            self.demo_mode = False
            logger.info("Loaded Silero-VAD via qai_hub_models.models.silero_vad.App")
            return
        except Exception as exc:  # noqa: BLE001
            logger.info("AI Hub silero_vad App unavailable (%s); trying torch.hub.", exc)

        try:
            import torch  # type: ignore

            vad_model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
            )
            self._torch_vad = vad_model
            self._get_speech_timestamps = utils[0]
            self.backend = "silero-vad-torch"
            self.demo_mode = False
            logger.info("Loaded Silero-VAD via torch.hub")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Silero-VAD unavailable (%s); energy fallback.", exc)
            self.demo_mode = True
            self.backend = "demo-energy"

    def detect_speech(self, audio_file_path: str) -> tuple[bool, float]:
        """Returns (is_speech, confidence) for a local audio file."""
        audio_bytes = PathBytes(audio_file_path)
        result = self.detect(audio_bytes, filename=os.path.basename(audio_file_path))
        return bool(result.get("has_speech")), float(result.get("speech_ratio") or 0.0)

    def detect(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict[str, Any]:
        y, sr = load_audio_16k(audio_bytes, filename)
        stats = audio_stats(y, sr)

        try:
            if self.model is not None:
                return self._run_qai(y, sr, stats)
            if self._torch_vad is not None and self._get_speech_timestamps is not None:
                return self._run_torch(y, sr, stats)
        except Exception as exc:  # noqa: BLE001
            logger.exception("VAD inference failed: %s", exc)

        return self._energy_vad(y, sr, stats)

    def _run_qai(self, y: np.ndarray, sr: int, stats: dict[str, Any]) -> dict[str, Any]:
        out: Any
        if hasattr(self.model, "detect_speech"):
            out = self.model.detect_speech(y)
        elif callable(self.model):
            out = self.model(y)
        else:
            raise RuntimeError("Silero VAD App has no detect interface")

        if isinstance(out, tuple) and len(out) >= 2:
            is_speech, confidence = bool(out[0]), float(out[1])
        elif isinstance(out, dict):
            is_speech = bool(out.get("is_speech") or out.get("has_speech"))
            confidence = float(out.get("confidence") or out.get("speech_ratio") or 0.0)
        else:
            is_speech = bool(out)
            confidence = 0.9 if is_speech else 0.1

        return {
            "has_speech": is_speech,
            "speech_ratio": round(confidence, 3),
            "segments": [],
            "trimmed_duration_s": stats.get("duration_s", 0.0) if is_speech else 0.0,
            "stats": stats,
            "backend": self.backend,
            "demo": False,
            "target_latency_ms": 20,
            "waveform_preview": _downsample_preview(y),
        }

    def _run_torch(self, y: np.ndarray, sr: int, stats: dict[str, Any]) -> dict[str, Any]:
        import torch  # type: ignore

        tensor = torch.from_numpy(y)
        stamps = self._get_speech_timestamps(tensor, self._torch_vad, sampling_rate=sr)
        segments = [
            {"start_s": round(s["start"] / sr, 3), "end_s": round(s["end"] / sr, 3)}
            for s in stamps
        ]
        if stamps:
            pieces = [y[s["start"] : s["end"]] for s in stamps]
            trimmed = np.concatenate(pieces) if pieces else y
        else:
            trimmed = y
        ratio = float(trimmed.size / max(1, y.size))
        return {
            "has_speech": len(segments) > 0,
            "segments": segments,
            "speech_ratio": round(ratio, 3),
            "trimmed_duration_s": round(float(trimmed.size / sr), 3),
            "stats": stats,
            "backend": self.backend,
            "demo": False,
            "target_latency_ms": 20,
            "waveform_preview": _downsample_preview(y),
        }

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
                "target_latency_ms": 20,
                "waveform_preview": [],
            }
        frame = max(1, int(0.03 * sr))
        energies = [
            float(np.sqrt(np.mean(np.square(y[i : i + frame]))))
            for i in range(0, len(y) - frame, frame)
        ]
        thr = max(0.01, float(np.median(energies)) * 1.5) if energies else 0.01
        speech_frames = [e >= thr for e in energies]
        ratio = sum(speech_frames) / max(1, len(speech_frames))
        segments = []
        start = None
        for idx, flagged in enumerate(speech_frames):
            if flagged and start is None:
                start = idx
            if not flagged and start is not None:
                segments.append(
                    {"start_s": round(start * frame / sr, 3), "end_s": round(idx * frame / sr, 3)}
                )
                start = None
        if start is not None:
            segments.append(
                {
                    "start_s": round(start * frame / sr, 3),
                    "end_s": round(len(speech_frames) * frame / sr, 3),
                }
            )
        return {
            "has_speech": ratio > 0.05 or stats.get("rms", 0) > 0.005,
            "segments": segments,
            "speech_ratio": round(float(ratio), 3),
            "trimmed_duration_s": round(float(ratio * stats.get("duration_s", 0)), 3),
            "stats": stats,
            "backend": self.backend,
            "demo": True,
            "target_latency_ms": 20,
            "waveform_preview": _downsample_preview(y),
        }


def PathBytes(path: str) -> bytes:
    return Path(path).read_bytes()


def _downsample_preview(y: np.ndarray, points: int = 48) -> list[float]:
    if y.size == 0:
        return [0.0] * points
    idx = np.linspace(0, y.size - 1, num=points).astype(int)
    return [round(float(abs(v)), 4) for v in y[idx]]


# Backward-compatible alias
VoiceActivityDetector = SileroVAD
