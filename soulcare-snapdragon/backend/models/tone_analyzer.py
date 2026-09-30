"""
Tone analysis from voice audio (librosa features) — complements Silero-VAD.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np

from utils.audio_preprocessing import load_audio_16k

logger = logging.getLogger("soulcare.tone")


class ToneAnalyzer:
    def __init__(self) -> None:
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.backend = "demo"
        self._librosa = None
        if os.getenv("FORCE_TONE", "0") == "1" or not self.demo_mode:
            self._try_load()

    def _try_load(self) -> None:
        try:
            import librosa  # type: ignore

            self._librosa = librosa
            self.backend = "librosa"
            self.demo_mode = False
            logger.info("Librosa tone analyzer ready.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Librosa unavailable (%s); demo tone.", exc)
            self.demo_mode = True
            self.backend = "demo"

    def analyze(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict[str, Any]:
        if self.demo_mode or self._librosa is None:
            return self._demo_analyze(audio_bytes)

        librosa = self._librosa
        y, sr = load_audio_16k(audio_bytes, filename)
        if y.size == 0:
            return self._demo_analyze(audio_bytes)

        rms = float(np.mean(librosa.feature.rms(y=y)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_vals = pitches[magnitudes > np.median(magnitudes)]
        pitch_std = float(np.std(pitch_vals)) if pitch_vals.size else 0.0
        arousal = min(1.0, (rms * 8) + (zcr * 2))
        tension = min(1.0, (pitch_std / 80.0) + (centroid / 4000.0))

        if arousal < 0.25 and tension < 0.3:
            tone = "calm"
        elif arousal < 0.45:
            tone = "reflective"
        elif tension > 0.55:
            tone = "anxious"
        else:
            tone = "distressed"

        return {
            "tone": tone,
            "features": {
                "rms_energy": round(rms, 5),
                "zero_crossing_rate": round(zcr, 5),
                "spectral_centroid": round(centroid, 2),
                "pitch_std": round(pitch_std, 2),
                "arousal": round(arousal, 3),
                "tension": round(tension, 3),
            },
            "backend": self.backend,
            "demo": False,
        }

    def _demo_analyze(self, audio_bytes: bytes) -> dict[str, Any]:
        size_kb = max(1, len(audio_bytes) // 1024)
        tones = ["calm", "reflective", "anxious", "distressed"]
        tone = tones[size_kb % len(tones)]
        return {
            "tone": tone,
            "features": {
                "rms_energy": 0.02 + (size_kb % 5) * 0.01,
                "zero_crossing_rate": 0.05,
                "spectral_centroid": 1200.0,
                "pitch_std": 20.0 + size_kb,
                "arousal": 0.3 + (size_kb % 4) * 0.1,
                "tension": 0.25 + (size_kb % 3) * 0.1,
            },
            "backend": self.backend,
            "demo": True,
        }
