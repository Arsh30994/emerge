# SoulCare Desktop

**Privacy-first mental health companion that runs 100% local AI on Snapdragon-powered HP PCs.**

Snapdragon AI Lab — Build & Present Challenge submission.

> Mental health conversations never leave the laptop. No OpenAI. No Gemini. No cloud APIs.

---

## Why Snapdragon

| Need | How Snapdragon helps |
|------|----------------------|
| Private inference | Whisper, risk model, and optional Phi-3 run on-device (NPU / Adreno GPU / CPU) |
| Low latency | No network round-trip to a cloud LLM |
| Offline use | Works in low-connectivity clinics, campuses, and homes |
| Efficient battery | NPU offload for STT + LLM; tiny sklearn risk model stays on CPU |

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full on-device map.

---

## Features (MVP)

1. **Voice input** — local Whisper transcription  
2. **Text input** — chat composer  
3. **Risk classification** — TF-IDF + Logistic Regression (crisis / high / moderate / low)  
4. **Tone analysis** — librosa energy / pitch / spectral features  
5. **Supportive replies** — rule-based by default; optional local Phi-3-mini  
6. **Offline mode** — demo path works without downloading large models  

---

## Quick start

### 1. Backend (required)

```bash
cd soulcare-snapdragon/backend
python -m venv ../.venv

# Windows
..\.venv\Scripts\activate
# macOS / Linux
source ../.venv/bin/activate

pip install -r requirements.txt
python main.py
```

API listens on `http://0.0.0.0:8000` (Render / LAN friendly). Health check: `GET /health`.

> **Demo mode (default):** `SOULCARE_DEMO=1` uses rule-based replies + stub Whisper/tone so judges can run the full UX without multi-GB model downloads. Real stacks:

```bash
# Real Whisper
set FORCE_WHISPER=1
set WHISPER_MODEL=base

# Real librosa tone
set FORCE_TONE=1

# Local Phi-3 (install transformers + torch first)
set FORCE_PHI3=1
set PHI3_MODEL=microsoft/Phi-3-mini-4k-instruct
```

### 2. Frontend (web UI)

```bash
cd soulcare-snapdragon/frontend
npm install
npm run dev:web
```

Open `http://127.0.0.1:5173`.

### 3. Electron desktop shell

```bash
cd soulcare-snapdragon/frontend
npm install
npm run dev
```

Electron spawns the FastAPI child process and loads the UI.  
Windows portable build:

```bash
npm run package:win
```

---

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + Snapdragon accel hint |
| GET | `/system` | Component backends |
| GET | `/metrics` | Latency / memory samples |
| POST | `/classify` | `{ "text": "..." }` → risk label |
| POST | `/chat` | classify + reply |
| POST | `/transcribe` | multipart audio → text |
| POST | `/analyze-tone` | multipart audio → tone |
| POST | `/voice-chat` | audio → STT → tone → risk → reply |

---

## Project layout

```
soulcare-snapdragon/
├── README.md
├── ARCHITECTURE.md
├── demo_script.md
├── requirements.txt
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── models/
│   │   ├── risk_classifier.py
│   │   ├── speech_to_text.py
│   │   ├── tone_analyzer.py
│   │   └── response_generator.py
│   └── utils/
│       └── snapdragon_optimization.py
├── frontend/
│   ├── package.json
│   ├── electron/main.js
│   └── src/
├── models/                 # risk_model.joblib (auto-trained on first run)
└── presentation/
    └── pitch_deck.md
```

---

## Performance notes (for judges)

- Every pipeline stage logs **latency_ms** and **memory_mb** via `PerformanceMonitor`.
- Inspect live samples: `GET http://127.0.0.1:8000/metrics`
- On Snapdragon X Elite, prefer:
  - Whisper / Phi-3 → **NPU** (ONNX Runtime QNN) or **GPU** (DirectML)
  - Risk classifier → **CPU** (sub-millisecond)

---

## Safety

SoulCare is a **supportive companion**, not therapy or an emergency service.  
Crisis language triggers helpline guidance (US **988**, IASP directory).  
If someone is in immediate danger, call local emergency services.

---

## License / models

- App code: MIT (hackathon submission)
- Whisper, Phi-3, scikit-learn, librosa: respective open-source licenses
