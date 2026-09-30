# SoulCare Desktop

**Privacy-first mental health companion** running **100% on-device AI** on Snapdragon X Elite / X Plus HP PCs.

Snapdragon AI Lab — Build & Present Challenge submission.

> Mental health conversations never leave the laptop. No OpenAI. No Gemini. Models from [Qualcomm AI Hub](https://github.com/qualcomm/ai-hub-models).

---

## Problem

Cloud chatbots send intimate mental-health transcripts off-device — privacy risk, compliance risk, and they fail offline.

## Solution

SoulCare Desktop keeps every byte local:

| Stage | Model (AI Hub) | Size | Snapdragon target |
|-------|----------------|------|-------------------|
| VAD | Silero-VAD | ~2MB | Real-time CPU |
| Speech-to-text | **Whisper-Small** | 244MB | 12.5× real-time |
| Risk | **Distil-BERT-Base-Uncased** | 67MB | 100+ inf/sec |
| Response | **Phi-3.5-Mini-Instruct** | 2.1GB | ~42 tok/s on X Elite |

Runtime: **ONNX Runtime + Qualcomm QNN EP** (Windows on Snapdragon). Alternative LLM path: `llama.cpp`.

## Snapdragon advantage

- **45 TOPS NPU** (X Elite) vs Apple M3 ~18 TOPS
- Offline-capable clinics / campuses / travel
- **$0 / inference** vs cloud API bills
- End-to-end target **&lt; 2s**, memory ~**2.5GB**

Docs: [ARCHITECTURE.md](./ARCHITECTURE.md) · AI Hub Workbench: https://workbench.aihub.qualcomm.com/docs/

---

## Quick start

### Backend

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

API: `http://0.0.0.0:8000` · Swagger: `/docs` · Health: `/health`

### Frontend

```bash
cd soulcare-snapdragon/frontend
npm install
npm run dev:web
```

Electron: `npm run dev` · Windows portable: `npm run package:win`

### Snapdragon HP PC (full NPU stack)

```bash
pip install "qai-hub-models[whisper-small]" qai_hub_models_cli torch transformers
qai-hub-models fetch Whisper-Small --runtime qnn_context_binary --precision float
qai-hub-models fetch Distil-Bert-Base-Uncased-Hf --runtime qnn_context_binary
qai-hub-models fetch Phi-3.5-Mini-Instruct --runtime qnn_context_binary --precision w4a16

set SOULCARE_DEMO=0
set SOULCARE_CLOUD_FALLBACK=0
set SOULCARE_ACCEL=npu
set FORCE_WHISPER=1
set FORCE_DISTILBERT=1
set FORCE_PHI35=1
set FORCE_VAD=1
python main.py
```

### Demo mode (default)

Works without multi-GB downloads for judges. Optional **non-Snapdragon** cloud fallbacks (Groq) only when `SOULCARE_CLOUD_FALLBACK=1` — **keep this OFF on device builds**.

```bash
cp .env.example .env   # add keys locally; never commit .env
```

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Model load status + AI Hub IDs |
| GET | `/benchmarks` | Latency, tok/s, targets |
| POST | `/transcribe` | Whisper-Small (+ VAD) |
| POST | `/assess-risk` | Distil-BERT risk score/level |
| POST | `/generate-response` | Phi-3.5 supportive reply |
| POST | `/voice-chat` | Full voice pipeline |
| POST | `/chat` | Text pipeline |
| POST | `/vad` | Silero / energy VAD |

---

## Performance targets

| Metric | Target |
|--------|--------|
| STT latency | &lt; 100ms (post-VAD chunk) |
| Risk classification | &lt; 50ms |
| LLM | ~42 tok/s |
| End-to-end | &lt; 2s |
| Memory | ~2.5GB |

Live samples: `GET /benchmarks`

---

## Safety

Companion ≠ clinician. Critical language surfaces **988** / IASP. No self-harm instructions.

## References

- https://github.com/qualcomm/ai-hub-models
- https://github.com/qualcomm/ai-hub-apps
- https://workbench.aihub.qualcomm.com/docs/
