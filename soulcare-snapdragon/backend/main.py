"""
SoulCare Desktop — FastAPI backend

Local-only mental health companion API for Snapdragon-powered HP PCs.
No cloud LLM / STT calls. Bind to 0.0.0.0 for Electron + LAN demos.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow `python main.py` from the backend/ directory
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.risk_classifier import RiskClassifier
from models.response_generator import ResponseGenerator
from models.speech_to_text import SpeechToText
from models.tone_analyzer import ToneAnalyzer
from utils.snapdragon_optimization import PerformanceMonitor, SnapdragonRuntime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("soulcare")

# Shared singletons loaded at startup
runtime = SnapdragonRuntime()
perf = PerformanceMonitor()
risk_clf: RiskClassifier | None = None
stt: SpeechToText | None = None
tone: ToneAnalyzer | None = None
responder: ResponseGenerator | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global risk_clf, stt, tone, responder
    logger.info("Starting SoulCare — accelerator=%s", runtime.preferred)
    risk_clf = RiskClassifier()
    stt = SpeechToText()
    tone = ToneAnalyzer()
    responder = ResponseGenerator()
    yield
    logger.info("SoulCare shutting down.")


app = FastAPI(
    title="SoulCare Desktop API",
    description="Privacy-first mental health assistant — on-device AI for Snapdragon HP PCs",
    version="1.0.0",
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


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": "SoulCare Desktop",
        "demo_mode": os.getenv("SOULCARE_DEMO", "1") == "1",
        "snapdragon": runtime.info,
    }


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    """Latency / memory samples for Snapdragon benchmarking."""
    return perf.summary()


@app.get("/system")
def system_info() -> dict[str, Any]:
    return {
        "snapdragon": runtime.info,
        "components": {
            "risk": "tfidf+logreg",
            "stt": getattr(stt, "backend", "pending"),
            "tone": getattr(tone, "backend", "pending"),
            "response": getattr(responder, "backend", "pending"),
        },
    }


@app.post("/classify")
def classify_risk(payload: TextIn) -> dict[str, Any]:
    """Risk / crisis classification (TF-IDF + Logistic Regression)."""
    assert risk_clf is not None
    with perf.track("risk_classify", backend=runtime.backend_for("risk")) as extra:
        result = risk_clf.predict(payload.text)
        extra["label"] = result["label"]
    return result


@app.post("/chat")
def chat(payload: ChatIn) -> dict[str, Any]:
    """Full text pipeline: classify → generate supportive reply."""
    assert risk_clf is not None and responder is not None
    with perf.track("chat_total", backend="pipeline") as extra:
        with perf.track("risk_classify", backend=runtime.backend_for("risk")):
            risk = risk_clf.predict(payload.text)
        with perf.track("response_generate", backend=runtime.backend_for("llm")):
            response = responder.generate(payload.text, risk, payload.tone)
        extra["risk"] = risk["label"]
    return {
        "user_text": payload.text,
        "risk": risk,
        "tone": payload.tone,
        "response": response,
        "metrics": perf.samples[-1].as_dict() if perf.samples else None,
    }


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Local Whisper speech-to-text."""
    assert stt is not None
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    with perf.track("stt_transcribe", backend=runtime.backend_for("stt")) as extra:
        result = stt.transcribe(audio, filename=file.filename or "audio.webm")
        extra["demo"] = result.get("demo", False)
    return result


@app.post("/analyze-tone")
async def analyze_tone(
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Voice tone features via librosa (or demo heuristics)."""
    assert tone is not None
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    with perf.track("tone_analyze", backend=runtime.backend_for("tone")):
        result = tone.analyze(audio, filename=file.filename or "audio.webm")
    return result


@app.post("/voice-chat")
async def voice_chat(
    file: UploadFile = File(...),
    include_tone: bool = Form(True),
) -> dict[str, Any]:
    """
    End-to-end voice path:
      audio → Whisper STT → tone → risk → local response
    """
    assert stt is not None and tone is not None and risk_clf is not None and responder is not None
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio upload")

    with perf.track("voice_chat_total", backend="pipeline") as extra:
        with perf.track("stt_transcribe", backend=runtime.backend_for("stt")):
            transcript = stt.transcribe(audio, filename=file.filename or "audio.webm")
        tone_result = None
        if include_tone:
            with perf.track("tone_analyze", backend=runtime.backend_for("tone")):
                tone_result = tone.analyze(audio, filename=file.filename or "audio.webm")
        text = transcript.get("text") or ""
        with perf.track("risk_classify", backend=runtime.backend_for("risk")):
            risk = risk_clf.predict(text)
        with perf.track("response_generate", backend=runtime.backend_for("llm")):
            response = responder.generate(text, risk, tone_result)
        extra["risk"] = risk["label"]

    return {
        "transcript": transcript,
        "tone": tone_result,
        "risk": risk,
        "response": response,
    }


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    # Reload off for packaged / Electron child process stability
    uvicorn.run("main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
