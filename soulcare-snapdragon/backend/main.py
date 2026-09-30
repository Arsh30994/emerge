"""SoulCare Desktop — FastAPI backend (Qualcomm AI Hub model stack)."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
load_dotenv(PROJECT / ".env")
load_dotenv(ROOT / ".env")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.response_generator import ResponseGenerator
from models.risk_classifier import RiskClassifier
from models.speech_to_text import SpeechToText
from models.tone_analyzer import ToneAnalyzer
from models.voice_activity import VoiceActivityDetector
from utils.snapdragon_benchmarks import SnapdragonBenchmarks
from utils.snapdragon_optimization import SnapdragonRuntime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("soulcare")

runtime = SnapdragonRuntime()
bench = SnapdragonBenchmarks()

risk_clf: RiskClassifier | None = None
stt: SpeechToText | None = None
tone: ToneAnalyzer | None = None
vad: VoiceActivityDetector | None = None
responder: ResponseGenerator | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global risk_clf, stt, tone, vad, responder
    logger.info(
        "SoulCare starting — accel=%s demo=%s cloud_fallback=%s",
        runtime.preferred,
        os.getenv("SOULCARE_DEMO", "1"),
        os.getenv("SOULCARE_CLOUD_FALLBACK", "0"),
    )
    risk_clf = RiskClassifier()
    stt = SpeechToText()
    tone = ToneAnalyzer()
    vad = VoiceActivityDetector()
    responder = ResponseGenerator()
    yield
    logger.info("SoulCare shutting down.")


app = FastAPI(
    title="SoulCare Desktop API",
    description=(
        "Privacy-first mental health assistant — Qualcomm AI Hub models "
        "(Whisper-Small, Distil-BERT, Phi-3.5-Mini) on Snapdragon NPU"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)


class ChatIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    tone: dict[str, Any] | None = None


class GenerateIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    risk_context: dict[str, Any] | None = None
    tone: dict[str, Any] | None = None


def _status_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": "SoulCare Desktop",
        "version": "2.0.0",
        "demo_mode": os.getenv("SOULCARE_DEMO", "1") == "1",
        "cloud_fallback": os.getenv("SOULCARE_CLOUD_FALLBACK", "0") == "1",
        "privacy": "On Snapdragon builds, all inference is on-device via AI Hub + QNN.",
        "models": {
            "stt": getattr(stt, "backend", "pending"),
            "vad": getattr(vad, "backend", "pending"),
            "risk": getattr(risk_clf, "backend", "pending"),
            "tone": getattr(tone, "backend", "pending"),
            "response": getattr(responder, "backend", "pending"),
        },
        "ai_hub": {
            "whisper_small": "qai_hub_models.models.whisper_small",
            "distil_bert": "qai_hub_models.models.distil_bert_base_uncased_hf",
            "phi_3_5_mini": "qai_hub_models.models.phi_3_5_mini_instruct",
            "silero_vad": "snakers4/silero-vad",
        },
        "snapdragon": runtime.info,
        "loaded": all(x is not None for x in (risk_clf, stt, tone, vad, responder)),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    """Model loading status for Electron + judges."""
    return _status_payload()


@app.get("/system")
def system_info() -> dict[str, Any]:
    return _status_payload()


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return bench.summary()


@app.get("/benchmarks")
def benchmarks() -> dict[str, Any]:
    return bench.summary()


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> dict[str, Any]:
    """Whisper-Small speech-to-text (AI Hub)."""
    assert stt is not None and vad is not None
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio upload")
    with bench.track("vad", backend=runtime.backend_for("tone")):
        vad_result = vad.detect(audio, filename=file.filename or "audio.webm")
    with bench.track("stt_transcribe", backend=runtime.backend_for("stt")) as extra:
        result = stt.transcribe(audio, filename=file.filename or "audio.webm")
        extra["demo"] = result.get("demo", False)
    result["vad"] = vad_result
    return result


@app.post("/assess-risk")
def assess_risk(payload: TextIn) -> dict[str, Any]:
    """Distil-BERT (or sklearn fallback) crisis / distress scoring."""
    assert risk_clf is not None
    with bench.track("risk_classify", backend=runtime.backend_for("risk")) as extra:
        result = risk_clf.predict(payload.text)
        extra["risk_level"] = result["risk_level"]
    return result


@app.post("/classify")
def classify_compat(payload: TextIn) -> dict[str, Any]:
    """Backward-compatible alias for /assess-risk."""
    return assess_risk(payload)


@app.post("/generate-response")
def generate_response(payload: GenerateIn) -> dict[str, Any]:
    """Phi-3.5-Mini supportive reply (local) with safe fallbacks."""
    assert risk_clf is not None and responder is not None
    risk = payload.risk_context or risk_clf.predict(payload.text)
    with bench.track(
        "response_generate",
        backend=runtime.backend_for("llm"),
    ) as extra:
        response = responder.generate(payload.text, risk, payload.tone)
        extra["tokens"] = response.get("tokens")
    return {"risk": risk, "response": response}


@app.post("/chat")
def chat(payload: ChatIn) -> dict[str, Any]:
    """Text pipeline: assess-risk → generate-response."""
    assert risk_clf is not None and responder is not None
    with bench.track("chat_total", backend="pipeline") as extra:
        with bench.track("risk_classify", backend=runtime.backend_for("risk")):
            risk = risk_clf.predict(payload.text)
        with bench.track("response_generate", backend=runtime.backend_for("llm")) as gextra:
            response = responder.generate(payload.text, risk, payload.tone)
            gextra["tokens"] = response.get("tokens")
        extra["risk"] = risk.get("risk_level")
    return {
        "user_text": payload.text,
        "risk": risk,
        "tone": payload.tone,
        "response": response,
        "metrics": bench.samples[-1].as_dict() if bench.samples else None,
    }


@app.post("/analyze-tone")
async def analyze_tone(file: UploadFile = File(...)) -> dict[str, Any]:
    assert tone is not None
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio upload")
    with bench.track("tone_analyze", backend=runtime.backend_for("tone")):
        return tone.analyze(audio, filename=file.filename or "audio.webm")


@app.post("/vad")
async def voice_activity(file: UploadFile = File(...)) -> dict[str, Any]:
    assert vad is not None
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio upload")
    with bench.track("vad", backend=runtime.backend_for("tone")):
        return vad.detect(audio, filename=file.filename or "audio.webm")


@app.post("/voice-chat")
async def voice_chat(
    file: UploadFile = File(...),
    include_tone: bool = Form(True),
) -> dict[str, Any]:
    """audio → VAD → Whisper-Small → tone → Distil-BERT → Phi-3.5."""
    assert all(x is not None for x in (stt, vad, tone, risk_clf, responder))
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio upload")

    with bench.track("voice_chat_total", backend="pipeline") as extra:
        with bench.track("vad", backend=runtime.backend_for("tone")):
            vad_result = vad.detect(audio, filename=file.filename or "audio.webm")
        with bench.track("stt_transcribe", backend=runtime.backend_for("stt")):
            transcript = stt.transcribe(audio, filename=file.filename or "audio.webm")
        tone_result = None
        if include_tone:
            with bench.track("tone_analyze", backend=runtime.backend_for("tone")):
                tone_result = tone.analyze(audio, filename=file.filename or "audio.webm")
        text = transcript.get("text") or ""
        with bench.track("risk_classify", backend=runtime.backend_for("risk")):
            risk = risk_clf.predict(text)
        with bench.track("response_generate", backend=runtime.backend_for("llm")) as gextra:
            response = responder.generate(text, risk, tone_result, vad_result)
            gextra["tokens"] = response.get("tokens")
        extra["risk"] = risk.get("risk_level")

    return {
        "vad": vad_result,
        "transcript": transcript,
        "tone": tone_result,
        "risk": risk,
        "response": response,
    }


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
