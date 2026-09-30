# SoulCare Desktop

**Privacy-first, agentic mental health companion** that runs **local AI** on Snapdragon X Elite / X Plus HP PCs.

Built for the **Snapdragon AI Lab Build & Present Challenge**.

> Your conversations stay on the laptop. Models come from [Qualcomm AI Hub](https://github.com/qualcomm/ai-hub-models). No OpenAI / Gemini required on device builds.

---

## What is SoulCare?

SoulCare is a desktop app (React + Electron) with a Python FastAPI brain. You can **type or speak**. The app:

1. Detects speech with **Silero-VAD**
2. Transcribes with **Whisper-Small** (AI Hub)
3. Scores distress with **Distil-BERT** (crisis-aware)
4. Runs an **agentic tool loop** (breathe, ground, helpline, reflective prompts)
5. Replies with **Phi-3.5-Mini** (or safe offline templates)

All of that is designed to execute on the Snapdragon **NPU** via ONNX Runtime + QNN.

---

## Why Snapdragon?

| Challenge | SoulCare on Snapdragon |
|-----------|------------------------|
| Cloud bots leak intimate data | Inference stays on-device |
| Needs internet | Offline-capable after model fetch |
| API cost per message | **$0 / inference** |
| Latency | No network round-trip; NPU acceleration |

**Headline hardware story**

- Snapdragon X Elite NPU ≈ **45 TOPS** (vs Apple M3 ≈ 18 TOPS)
- Whisper-Small ≈ **12.5× real-time**
- Distil-BERT ≈ **100+ inf/sec**
- Phi-3.5-Mini ≈ **~42 tok/s** (device / precision dependent)
- End-to-end target **&lt; 2 seconds**, ~**2.5GB** working set

---

## Features

### Core AI
- Voice + text chat
- Real-time VAD level meter
- Risk pulse: `low` → `medium` → `high` → `critical`
- **Agentic AI** with observable tool trail
- Breathing exercise (4-7-8) + grounding tools

### Product essentials
- **Login / Register / Guest / Logout** (local accounts only)
- **Dark / Light theme**
- Mood check-in chips
- Export conversation (JSON)
- Clear chat
- Settings drawer
- Offline / Running Locally badge
- Latency benchmarks (`/benchmarks`)

### Demo accounts (on-device)
| User | Password |
|------|----------|
| `demo` | `demo123` |
| `judge` | `snapdragon` |

---

## Project layout

```
soulcare-snapdragon/
├── README.md
├── ARCHITECTURE.md
├── demo_script.md
├── backend/
│   ├── main.py                 # FastAPI
│   ├── requirements.txt
│   ├── models/                 # agent, auth, STT, VAD, risk, reply
│   └── utils/                  # audio, benchmarks, Snapdragon runtime
├── frontend/                   # React + Electron + Vite
├── models/                     # AI Hub assets + local users.json
├── scripts/fetch_ai_hub_models.sh
└── presentation/pitch_deck.md
```

---

## Quick start

### 1) Backend

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

API: `http://127.0.0.1:8000` · Docs: `/docs` · Health: `/health`

### 2) Frontend

```bash
cd soulcare-snapdragon/frontend
npm install
npm run dev:web
```

Open `http://127.0.0.1:5173` → log in with `demo / demo123`.

### 3) Electron desktop

```bash
npm run dev
npm run package:win   # portable .exe for Snapdragon HP PCs
```

---

## Agentic AI

`POST /chat` and `POST /voice-chat` run **SoulCare Agent** by default (`agentic: true`).

**Loop:** observe → plan tools → act → respond

| Tool | When |
|------|------|
| `assess_risk` | Always |
| `breathing_guide` | Medium/high / anxious tone |
| `grounding_54321` | High distress |
| `helpline_resources` | High/critical |
| `safety_plan_nudge` | Critical |
| `mood_checkin` / `reflective_prompt` | Low/medium |

The UI shows the **Agent trail** so judges can see tool selection live.

---

## Snapdragon / AI Hub setup

```bash
pip install "qai-hub-models[whisper-small]" qai_hub_models_cli torch transformers
./scripts/fetch_ai_hub_models.sh

set SOULCARE_DEMO=0
set SOULCARE_CLOUD_FALLBACK=0
set SOULCARE_ACCEL=npu
set FORCE_WHISPER=1
set FORCE_DISTILBERT=1
set FORCE_PHI35=1
set FORCE_VAD=1
python main.py
```

References:

- https://github.com/qualcomm/ai-hub-models
- https://github.com/qualcomm/ai-hub-apps
- https://workbench.aihub.qualcomm.com/docs/

---

## API map

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Status, models, demo users |
| POST | `/auth/login` `/register` `/guest` `/logout` | Local auth |
| POST | `/chat` | Agentic text pipeline |
| POST | `/voice-chat` | VAD → STT → agent |
| POST | `/assess-risk` | Distil-BERT / fallback |
| POST | `/transcribe` | Whisper-Small |
| GET | `/benchmarks` | Latency / tok/s / targets |
| GET | `/exercises/breathing` | 4-7-8 metadata |

---

## Modes

| Mode | Env | Use |
|------|-----|-----|
| Demo (default) | `SOULCARE_DEMO=1` | Instant judge walkthrough without multi-GB downloads |
| Snapdragon NPU | `SOULCARE_DEMO=0`, `SOULCARE_ACCEL=npu` | Real AI Hub models |
| Optional cloud fallback | `SOULCARE_CLOUD_FALLBACK=1` + local `.env` keys | Non-Snapdragon laptops only — **not** the privacy pitch |

Never commit `.env`.

---

## Safety

SoulCare is a **supportive companion**, not a clinician or emergency service.  
Critical language triggers helpline guidance (**988** / IASP).  
If someone is in immediate danger, call local emergency services.

---

## License

Hackathon submission code: MIT-style use for the challenge.  
Model licenses: Whisper, Distil-BERT, Phi-3.5, Silero, Qualcomm AI Hub — see upstream.
