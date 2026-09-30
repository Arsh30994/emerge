"""
Speech-to-Text — Whisper-Small via Qualcomm AI Hub Models.

Load order (privacy-first):
  1. qai_hub_models.models.whisper_small  (Snapdragon / AI Hub)
  2. openai-whisper / transformers whisper-small (local PyTorch)
  3. Optional Groq Whisper (ONLY if SOULCARE_CLOUD_FALLBACK=1)
  4. Deterministic demo transcript
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from utils.audio_preprocessing import load_audio_16k, pcm16_bytes

logger = logging.getLogger("soulcare.stt")


class SpeechToText:
    def __init__(self, model_size: str | None = None) -> None:
        self.model_size = model_size or os.getenv("WHISPER_MODEL", "small")
        self.demo_mode = os.getenv("SOULCARE_DEMO", "1") == "1"
        self.cloud_fallback = os.getenv("SOULCARE_CLOUD_FALLBACK", "0") == "1"
        self.backend = "demo"
        self._whisper = None
        self._qai_app = None
        self._try_load_local()

    def _try_load_local(self) -> None:
        force = os.getenv("FORCE_WHISPER", "0") == "1"
        if self.demo_mode and not force:
            logger.info("STT demo mode (FORCE_WHISPER=1 for Whisper-Small).")
            return

        # 1) Qualcomm AI Hub
        try:
            from qai_hub_models.models.whisper_small import Model as WhisperSmall  # type: ignore
            from qai_hub_models.models.whisper_small.app import WhisperApp  # type: ignore

            model = WhisperSmall.from_pretrained()
            self._qai_app = WhisperApp(model)
            self.backend = "qai-hub-whisper-small"
            self.demo_mode = False
            logger.info("Loaded Whisper-Small from Qualcomm AI Hub Models")
            return
        except Exception as exc:  # noqa: BLE001
            logger.info("qai_hub whisper_small not loaded (%s)", exc)

        # 2) openai-whisper package
        try:
            import whisper  # type: ignore

            self._whisper = whisper.load_model(self.model_size)
            self.backend = f"openai-whisper-{self.model_size}"
            self.demo_mode = False
            logger.info("Loaded openai-whisper model=%s", self.model_size)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Local Whisper unavailable (%s).", exc)

        self.demo_mode = True
        self.backend = "demo"

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict[str, Any]:
        if self._qai_app is not None:
            try:
                return self._transcribe_qai(audio_bytes, filename)
            except Exception as exc:  # noqa: BLE001
                logger.warning("AI Hub Whisper failed (%s)", exc)

        if self._whisper is not None:
            try:
                return self._transcribe_openai_whisper(audio_bytes, filename)
            except Exception as exc:  # noqa: BLE001
                logger.warning("openai-whisper failed (%s)", exc)

        if self.cloud_fallback and os.getenv("GROQ_API_KEY"):
            try:
                return self._transcribe_groq(audio_bytes, filename)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Groq STT fallback failed (%s)", exc)

        return self._demo_transcribe(audio_bytes, filename)

    def _transcribe_qai(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
        y, _sr = load_audio_16k(audio_bytes, filename)
        # AI Hub WhisperApp APIs vary by version; try common call shapes
        text = None
        if hasattr(self._qai_app, "transcribe"):
            text = self._qai_app.transcribe(y)
        elif hasattr(self._qai_app, "predict"):
            text = self._qai_app.predict(y)
        else:
            raise RuntimeError("WhisperApp has no transcribe/predict")
        if isinstance(text, (list, tuple)):
            text = text[0]
        return {
            "text": str(text).strip(),
            "language": "en",
            "backend": self.backend,
            "model": "Whisper-Small (Qualcomm AI Hub)",
            "demo": False,
        }

    def _transcribe_openai_whisper(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
        suffix = Path(filename).suffix or ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            path = tmp.name
        try:
            result = self._whisper.transcribe(path, fp16=False)
            return {
                "text": (result.get("text") or "").strip(),
                "language": result.get("language", "en"),
                "backend": self.backend,
                "model": f"whisper-{self.model_size}",
                "demo": False,
            }
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _transcribe_groq(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
        """Optional non-Snapdragon demo path — disabled on device builds."""
        import urllib.request

        # Prefer wav PCM for broad STT compatibility
        y, sr = load_audio_16k(audio_bytes, filename)
        wav_path = None
        try:
            import wave

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm16_bytes(y))

            boundary = "----SoulCareBoundary"
            with open(wav_path, "rb") as f:
                file_data = f.read()
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
                f"Content-Type: audio/wav\r\n\r\n"
            ).encode() + file_data + (
                f"\r\n--{boundary}\r\n"
                f'Content-Disposition: form-data; name="model"\r\n\r\n'
                f"whisper-large-v3\r\n"
                f"--{boundary}--\r\n"
            ).encode()

            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                data=body,
                headers={
                    "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                import json

                payload = json.loads(resp.read().decode())
            return {
                "text": (payload.get("text") or "").strip(),
                "language": payload.get("language", "en"),
                "backend": "groq-whisper-fallback",
                "model": "whisper-large-v3 (Groq fallback — not used on Snapdragon)",
                "demo": False,
                "cloud_fallback": True,
            }
        finally:
            if wav_path:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

    def _demo_transcribe(self, audio_bytes: bytes, filename: str) -> dict[str, Any]:
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
            "model": "demo-stub (enable Whisper-Small from AI Hub on Snapdragon)",
            "demo": True,
            "note": "Set FORCE_WHISPER=1 or install qai-hub-models[whisper-small].",
            "filename": filename,
            "audio_kb": size_kb,
        }
