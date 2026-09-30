# SoulCare Architecture

## System diagram

```
┌─────────────────────────────────────────────────────────────┐
│                 SoulCare Desktop (Electron)                 │
│  React UI  ·  VoiceInput  ·  ChatInterface  ·  RiskIndicator │
└────────────────────────────┬────────────────────────────────┘
                             │  localhost HTTP
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI backend (Python, on-device)             │
│                                                             │
│   /voice-chat ──► Whisper STT ──► Tone (librosa)            │
│                         │                │                  │
│                         ▼                ▼                  │
│                   Risk Classifier ◄── user text             │
│                   (TF-IDF + LogReg)                         │
│                         │                                   │
│                         ▼                                   │
│               Response Generator                            │
│               (rules  |  Phi-3-mini local)                  │
│                         │                                   │
│                         ▼                                   │
│               PerformanceMonitor (latency, RSS)             │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Snapdragon X / X Elite HP PC                   │
│   Hexagon NPU  ·  Adreno GPU  ·  Oryon CPU  ·  LPDDR        │
│   All tensors & audio buffers stay in local memory          │
└─────────────────────────────────────────────────────────────┘
```

## Data flow (privacy)

1. Microphone audio is captured in the Chromium/Electron renderer.
2. Bytes are posted to `127.0.0.1` only — never to a public STT API.
3. Whisper (or demo STT) returns text in-process.
4. Risk + tone models score the utterance locally.
5. A supportive reply is generated locally (rules or Phi-3).
6. Optional metrics are kept in-memory for the `/metrics` endpoint.

**No telemetry leaves the device in the MVP.**

## Snapdragon integration

| Workload | Model | Preferred accelerator | Notes |
|----------|-------|-----------------------|-------|
| Speech-to-text | Whisper `base` / `small` | **NPU** (QNN) or **GPU** (DirectML) | Export ONNX; INT8 for NPU |
| Risk | sklearn TF-IDF + LogReg | **CPU** | ~KB model; NPU not needed |
| Tone | librosa RMS / ZCR / pitch | **CPU** / Hexagon DSP | Feature extract only |
| Response | Phi-3-mini-4k INT4/INT8 | **NPU** / **GPU** | ONNX Runtime GenAI / ExecuTorch |

### Enabling hardware EP (Windows on Snapdragon)

```text
1. Install Qualcomm AI Hub / ONNX Runtime with QNN execution provider
2. Export Whisper encoder/decoder to ONNX
3. Set SOULCARE_ACCEL=npu   (or gpu)
4. Point FORCE_WHISPER=1 / FORCE_PHI3=1 at the optimized graphs
```

`backend/utils/snapdragon_optimization.py` detects ARM/Qualcomm when possible and records the preferred unit in `/system` and `/health`.

## Why this architecture wins the Snapdragon story

- **Local inference only** — cloud LLMs are explicitly out of scope.
- **Heterogeneous compute** — heavy neural nets → NPU/GPU; classical ML → CPU.
- **Measurable** — every stage emits latency + memory for live demos.
- **Graceful demo mode** — judges can run the full path without multi-GB downloads, then flip env flags for the real stack on HP Snapdragon hardware.

## Threat / safety model

- Crisis keywords + classifier escalate UI + helpline copy.
- Response generator refuses to provide self-harm methods (prompt + crisis templates).
- Electron uses `contextIsolation` and no Node integration in the renderer.
