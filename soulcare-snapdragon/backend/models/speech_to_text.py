"""
Speech-to-Text — Whisper-Small via Qualcomm AI Hub.

Primary API (Snapdragon / AI Hub):
    from qai_hub_models.models.whisper_small import App
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from utils.audio_preprocessing import load_audio_16k, pcm16_bytes

logger = logging.getLogger("soulcare.stt")


class WhisperSTT:
    """Whisper-Small STT with graceful offline demo fallback."""

    def __init__(self) -> None:
        self.model_size = os.getenv("WHISPER_MODEL", "small")
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.backend = "demo"
        self.model: Any = None
        self._openai_whisper = None
        self._try_load()

    def _try_load(self) -> None:
        force = os.getenv("FORCE_WHISPER", "0") == "1"
        if self.demo_mode and not force:
            logger.info("WhisperSTT demo mode (set FORCE_WHISPER=1 for AI Hub Whisper-Small).")
            return

        # Qualcomm AI Hub — exact import path from hackathon brief
        try:
            from qai_hub_models.models.whisper_small import App  # type: ignore

            self.model = App()
            self.backend = "qai-hub-whisper-small"
            self.demo_mode = False
            logger.info("Loaded Whisper-Small via qai_hub_models.models.whisper_small.App")
            return
        except Exception as exc:  # noqa: BLE001
            logger.info("AI Hub Whisper App unavailable (%s); trying openai-whisper.", exc)

        try:
            import whisper  # type: ignore

            self._openai_whisper = whisper.load_model(self.model_size)
            self.backend = f"openai-whisper-{self.model_size}"
            self.demo_mode = False
            logger.info("Loaded openai-whisper fallback model=%s", self.model_size)
        except Exception as exc:  # noqa: BLE001
            logger.warning("No local Whisper available (%s); using demo STT.", exc)
            self.demo_mode = True
            self.backend = "demo"

    def transcribe_file(self, audio_file_path: str) -> str:
        """Transcribe a local audio path → text (AI Hub App or fallback)."""
        path = Path(audio_file_path)
        audio_bytes = path.read_bytes()
        return self.transcribe(audio_bytes, filename=path.name).get("text", "")

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict[str, Any]:
        """Transcribe audio bytes; returns structured payload for the API."""
        try:
            if self.model is not None:
                return self._run_qai(audio_bytes, filename)
            if self._openai_whisper is not None:
                return self._run_openai(audio_bytes, filename)
        except Exception as exc:  # noqa: BLE001
            logger.exception("STT inference failed: %s", exc)

        return self._demo(audio_bytes, filename)

    def _run_qai(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
        y, sr = load_audio_16k(audio_bytes, filename)
        # Persist temp wav — many AI Hub Apps expect a path
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            self._write_wav(tmp.name, y, sr)
            tmp_path = tmp.name
        try:
            text: Any
            if hasattr(self.model, "transcribe"):
                text = self.model.transcribe(tmp_path)
            elif callable(self.model):
                text = self.model(tmp_path)
            elif hasattr(self.model, "predict"):
                text = self.model.predict(tmp_path)
            else:
                raise RuntimeError("Whisper App has no transcribe/predict interface")
            if isinstance(text, (list, tuple)):
                text = text[0]
            return {
                "text": str(text).strip(),
                "language": "en",
                "backend": self.backend,
                "model": "Whisper-Small (qai_hub_models)",
                "demo": False,
                "target_latency_ms": 100,
            }
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _run_openai(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            path = tmp.name
        try:
            result = self._openai_whisper.transcribe(path, fp16=False)
            return {
                "text": (result.get("text") or "").strip(),
                "language": result.get("language", "en"),
                "backend": self.backend,
                "model": f"whisper-{self.model_size}",
                "demo": False,
                "target_latency_ms": 100,
            }
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _demo(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
        size_kb = max(1, len(audio_bytes) // 1024)
        samples = [
            "I've been feeling anxious about work lately and just needed to talk.",
            "Today was hard. I feel overwhelmed and a bit alone.",
            "I'm okay, just checking in. Could use some encouragement.",
            "I can't shake this heavy feeling and I'm worried about myself.",
        ]
        return {
            "text": samples[size_kb % len(samples)],
            "language": "en",
            "backend": "demo",
            "model": "demo-stub (install qai_hub_models Whisper-Small on Snapdragon)",
            "demo": True,
            "target_latency_ms": 100,
            "filename": filename,
        }

    @staticmethod
    def _write_wav(path: str, y, sr: int) -> None:
        import wave

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm16_bytes(y))


# Backward-compatible alias used by main.py
SpeechToText = WhisperSTT
