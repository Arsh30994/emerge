# SoulCare Desktop

**Privacy-first, on-device mental health AI** for Snapdragon X Elite / X Plus HP PCs.

Snapdragon AI Lab Build & Present Challenge — portfolio / demo MVP.

> 🔒 **Running Locally — 100% Private.** No OpenAI, Gemini, or Anthropic. All inference stays on-device via [Qualcomm AI Hub](https://aihub.qualcomm.com/models) models + QNN.

---

## Problem

Cloud mental-health chatbots send intimate transcripts off-device. That creates privacy risk, compliance risk, and fails offline.

## Solution

SoulCare Desktop keeps every byte local:

| Stage | Model | AI Hub import | Target |
|-------|-------|---------------|--------|
| VAD | Silero-VAD (~2MB) | `qai_hub_models.models.silero_vad.App` | &lt;20ms |
| STT | Whisper-Small (244MB) | `qai_hub_models.models.whisper_small.App` | &lt;100ms |
| Risk | Distil-BERT (67MB) | `qai_hub_models.models.distilbert_base_uncased.App` | &lt;50ms |
| Reply | Phi-3.5-Mini (2.1GB) | `qai_hub_models.models.phi_3_5_mini_instruct.App` | 500–1500ms / ~42 tok/s |

**End-to-end &lt; 2s** · **~2.5GB** working set · **45 TOPS** NPU story vs Apple M3 ~18 TOPS.

---

## Tech stack

- **Frontend:** React 18 + **TypeScript** + **TailwindCSS** + Electron (Windows ARM64/x64)
- **Backend:** Python 3.10+ · FastAPI · Pydantic · Uvicorn
- **Runtime:** ONNX Runtime + Qualcomm QNN EP (llama.cpp optional for Phi-3.5)
- **Agentic loop:** assess → breathe/ground/helpline tools → respond

---

## Quick start

### Backend

```bash
cd soulcare-snapdragon/backend
python -m venv ../.venv
# Windows: ..\.venv\Scripts\activate
source ../.venv/bin/activate
pip install -r requirements.txt
python main.py
```

API: `http://127.0.0.1:8000` · Swagger `/docs` · Health `/health`

### Frontend

```bash
cd soulcare-snapdragon/frontend
npm install
npm run dev:web
```

Open `http://127.0.0.1:5173` → login `demo` / `demo123`.

### Electron (Windows ARM64 for Snapdragon)

```bash
npm run package:win
```

### Full AI Hub models on Snapdragon HP PC

```bash
pip install qai_hub_models qai_hub_models_cli
pip install "qai-hub-models[whisper-small]"
./scripts/fetch_ai_hub_models.sh
set SOULCARE_DEMO=0
set SOULCARE_ACCEL=npu
set FORCE_WHISPER=1
set FORCE_DISTILBERT=1
set FORCE_PHI35=1
set FORCE_VAD=1
python main.py
```

Demo mode (default) runs without multi-GB downloads so judges can still walk the UX.

---

## API (must-have endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Model load status + latency targets |
| POST | `/transcribe` | Whisper-Small STT |
| POST | `/assess-risk` | Distil-BERT risk_score + risk_level |
| POST | `/respond` | Phi-3.5 supportive reply |
| POST | `/chat` / `/voice-chat` | Full agentic pipelines |
| GET | `/benchmarks` | Live latency samples |

---

## Privacy guarantees

- No cloud LLM/STT calls in the product path
- Auth accounts stored locally (`models/users.json`)
- Network monitor should show **zero** model API egress during use
- Offline-capable once AI Hub assets are cached

---

## Resources

- https://aihub.qualcomm.com/models
- https://github.com/qualcomm/ai-hub-models
- https://workbench.aihub.qualcomm.com/docs/
- `pip install qai_hub_models qai_hub_models_cli`

See also [ARCHITECTURE.md](./ARCHITECTURE.md) · [demo_script.md](./demo_script.md) · [presentation/pitch_deck.md](./presentation/pitch_deck.md)
