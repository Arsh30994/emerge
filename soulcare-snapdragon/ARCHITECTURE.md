# SoulCare Architecture — Qualcomm AI Hub on Snapdragon

## System diagram

```
┌────────────────────────────────────────────────────────────────┐
│              SoulCare Desktop (Electron + React)               │
│  VoiceInput + VAD meter · Chat · RiskIndicator · OfflineBadge  │
└─────────────────────────────┬──────────────────────────────────┘
                              │ localhost only
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    FastAPI (on-device)                          │
│                                                                │
│  audio ─► Silero-VAD ─► Whisper-Small (AI Hub)                 │
│                              │                                 │
│                              ▼                                 │
│                     Distil-BERT risk                           │
│                     (low/medium/high/critical)                 │
│                              │                                 │
│                              ▼                                 │
│                  Phi-3.5-Mini-Instruct                         │
│                  (supportive reply + safety)                   │
│                              │                                 │
│                     SnapdragonBenchmarks                       │
│                     (latency, tok/s, RSS)                      │
└─────────────────────────────┬──────────────────────────────────┘
                              ▼
┌────────────────────────────────────────────────────────────────┐
│           Snapdragon X Elite / X Plus HP PC                    │
│     Hexagon NPU (45 TOPS) · Adreno GPU · Oryon CPU             │
│     ONNX Runtime + QNN EP  ·  QAIRT                            │
└────────────────────────────────────────────────────────────────┘
```

## Model choices (AI Hub)

| Role | Package | Why |
|------|---------|-----|
| STT | `qai_hub_models.models.whisper_small` | 244MB, 12.5× RT on Snapdragon |
| VAD | Silero-VAD | ~2MB gate before Whisper |
| Risk | `distil_bert_base_uncased_hf` | 67MB, 100+ inf/sec |
| LLM | `phi_3_5_mini_instruct` | 2.1GB, ~42 tok/s w4a16 NPU |

Fetch assets:

```bash
qai-hub-models fetch Whisper-Small --runtime qnn_context_binary
qai-hub-models fetch Phi-3.5-Mini-Instruct --runtime qnn_context_binary --precision w4a16
```

Sample native apps: https://github.com/qualcomm/ai-hub-apps  
Workbench docs: https://workbench.aihub.qualcomm.com/docs/

## NPU utilization

1. **Whisper-Small encoder/decoder** → NPU (QNN) or GPU (DirectML)
2. **Distil-BERT** → NPU INT8/FP
3. **Phi-3.5-Mini** → NPU w4a16 context binary (or llama.cpp)
4. **Silero-VAD + librosa** → CPU (overkill for NPU)

`SOULCARE_ACCEL=npu|gpu|cpu` selects the preferred unit reported in `/health`.

## Privacy & offline

- Renderer → `127.0.0.1` only
- No OpenAI / Gemini on Snapdragon builds (`SOULCARE_CLOUD_FALLBACK=0`)
- Optional Groq fallback exists **only** for non-Snapdragon hackathon laptops — never the production story
- Works without internet once AI Hub assets are cached under `models/`

## Performance budget

| Stage | Budget |
|-------|--------|
| VAD | &lt; 10ms |
| Whisper-Small | &lt; 100ms (chunk) |
| Distil-BERT | &lt; 50ms |
| Phi-3.5 | 42 tok/s |
| E2E | &lt; 2s |
| RSS | ~2.5GB |

## Safety path

Critical keyword net + classifier → helpline templates (988 / IASP).  
Phi-3.5 system prompt forbids self-harm methods; critical turns use fixed templates.
