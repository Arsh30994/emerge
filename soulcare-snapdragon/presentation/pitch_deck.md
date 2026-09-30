# SoulCare Pitch Deck

Snapdragon AI Lab — Build & Present Challenge

---

## Slide 1 — Problem
Cloud AI privacy concerns: mental-health transcripts leave the device; offline users are stranded; API costs scale with suffering.

## Slide 2 — Solution
**SoulCare Desktop** — privacy-first companion with 100% on-device inference on Snapdragon HP PCs.

## Slide 3 — How It Works
Mic → Silero-VAD → Whisper-Small → Distil-BERT risk → Phi-3.5-Mini reply → UI risk pulse. FastAPI + Electron. Localhost only.

## Slide 4 — Why Snapdragon
- Hexagon NPU **45 TOPS** (vs Apple M3 ~18 TOPS)
- Offline + private + low latency
- ONNX Runtime + **QNN** execution provider
- $0 per inference

## Slide 5 — Model Choices (AI Hub)
| Model | Role | Size |
|-------|------|------|
| Whisper-Small | STT | 244MB |
| Silero-VAD | Speech gate | ~2MB |
| Distil-BERT | Risk | 67MB |
| Phi-3.5-Mini-Instruct | Response | 2.1GB |

Sources: [ai-hub-models](https://github.com/qualcomm/ai-hub-models) · [ai-hub-apps](https://github.com/qualcomm/ai-hub-apps)

## Slide 6 — Performance
- STT &lt; 100ms · Risk &lt; 50ms · ~42 tok/s · E2E &lt; 2s · ~2.5GB RAM  
- Live: `GET /benchmarks`

## Slide 7 — Impact
Privacy for students & workers · Accessibility offline · Trust via OfflineBadge · Crisis routing to 988

## Slide 8 — Demo
Live voice + text on HP Snapdragon laptop; show NPU accelerator field in `/health`.

## Slide 9 — Future
Multimodal VLM mood cues · camera-based affect (on-device) · clinician dashboard that never sees raw audio off-box · tighter QNN graphs from AI Hub Workbench
