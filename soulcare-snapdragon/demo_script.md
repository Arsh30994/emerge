# SoulCare Demo Script (3 minutes)

## Setup

```bash
cd soulcare-snapdragon/backend
..\.venv\Scripts\activate
python main.py
```

```bash
cd soulcare-snapdragon/frontend
npm run dev:web
```

Open UI + keep `/docs` or `/benchmarks` ready.

---

## 0:00 — Problem (20s)

> “Cloud mental-health bots ship intimate data off-device. SoulCare keeps every word on this Snapdragon PC.”

Point to **Running Locally** badge.

## 0:20 — Text path (40s)

Type: `I've been stressed about deadlines and can't sleep.`  
Show **medium/high** risk pulse (Distil-BERT) + supportive reply.

## 1:00 — Crisis safety (30s)

Type a brief crisis phrase. Show **critical** + 988 banner.  
> “Detection only — we route to human help.”

## 1:30 — Voice + VAD (50s)

Tap to talk → show VAD meter → Whisper-Small transcript → tone → reply.  
Name the AI Hub models out loud.

## 2:20 — Snapdragon story (30s)

Open `/benchmarks` or `/health`:

- 45 TOPS NPU vs M3 18 TOPS  
- Whisper 12.5× RT · Distil-BERT 100+ ips · Phi-3.5 ~42 tok/s  
- ONNX Runtime + QNN · $0/inference · offline

## 2:50 — Close (10s)

> “Private mental health AI is practical because Snapdragon runs Qualcomm AI Hub models on-device.”

## Backup

Text-only + `/assess-risk` in Swagger if mic fails.
