"""
Speech-to-text using OpenAI Whisper (local).

Falls back to a demo transcription path when Whisper/torch are
unavailable so judges can still walk through the full UX offline.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("soulcare.stt")


class SpeechToText:
    """Local Whisper wrapper with graceful demo fallback."""

    def __init__(self, model_size: str | None = None) -> None:
        # tiny/base/small are better for Snapdragon NPU demos; medium for accuracy
        self.model_size = model_size or os.getenv("WHISPER_MODEL", "base")
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self._model = None
        self.backend = "demo"
        self._try_load()

    def _try_load(self) -> None:
        if self.demo_mode and os.getenv("FORCE_WHISPER", "0") != "1":
            logger.info("STT running in demo mode (set FORCE_WHISPER=1 to load Whisper).")
            return
        try:
            import whisper  # type: ignore

            self._model = whisper.load_model(self.model_size)
            self.backend = f"whisper-{self.model_size}"
            self.demo_mode = False
            logger.info("Loaded Whisper model: %s", self.model_size)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Whisper unavailable (%s); using demo STT.", exc)
            self.demo_mode = True
            self.backend = "demo"

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict[str, Any]:
        """Transcribe audio bytes to text on-device."""
        if self.demo_mode or self._model is None:
            return self._demo_transcribe(audio_bytes, filename)

        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = self._model.transcribe(tmp_path, fp16=False)
            text = (result.get("text") or "").strip()
            return {
                "text": text,
                "language": result.get("language", "en"),
                "backend": self.backend,
                "demo": False,
            }
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _demo_transcribe(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
        """Deterministic demo transcript so UI flows work without Whisper."""
        size_kb = max(1, len(audio_bytes) // 1024)
        # Rotate a few supportive demo utterances based on audio size
        samples = [
            "I've been feeling anxious about work lately and just needed to talk.",
            "Today was hard. I feel overwhelmed and a bit alone.",
            "I'm okay, just checking in. Could use some encouragement.",
            "I can't shake this heavy feeling and I'm worried about myself.",
        ]
        text = samples[size_kb % len(samples)]
        return {
            "text": text,
            "language": "en",
            "backend": self.backend,
            "demo": True,
            "note": "Demo STT — install Whisper and set FORCE_WHISPER=1 for real local transcription.",
            "filename": filename,
            "audio_kb": size_kb,
        }
