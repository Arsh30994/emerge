# SoulCare Pitch Deck (speaker notes)

Snapdragon AI Lab — Build & Present Challenge

---

## Slide 1 — Title

**SoulCare**  
On-device mental health companion for Snapdragon HP PCs

Tagline: *Your feelings stay on your laptop.*

---

## Slide 2 — Problem

- Mental health support is increasingly mediated by **cloud LLMs**
- Sensitive transcripts leave the device → privacy, compliance, trust risk
- Connectivity gaps (dorms, clinics, travel) break cloud-only tools
- Students need something **immediate, private, and safe**

---

## Slide 3 — Solution

SoulCare Desktop:

1. Speak or type
2. Local Whisper understands you
3. On-device risk + tone models listen for distress
4. Supportive reply generated locally (rules / Phi-3-mini)
5. Crisis language surfaces **988 / local helplines**

**Zero cloud AI calls.**

---

## Slide 4 — Why Snapdragon

| Cloud chatbot | SoulCare on Snapdragon |
|---------------|------------------------|
| Data leaves device | Data never leaves PC |
| Network latency | Local NPU/GPU inference |
| Needs internet | Offline-capable |
| Generic hardware | Tuned for Hexagon NPU + Adreno |

Heterogeneous map:

- Whisper / Phi-3 → **NPU or GPU**
- Risk (TF-IDF + LogReg) → **CPU**
- Tone features → **CPU / DSP**

---

## Slide 5 — Product demo highlights

- Electron + React desktop shell
- FastAPI local backend
- Live risk pulse + voice tone
- `/metrics` latency & memory for judges

---

## Slide 6 — Tech stack (open source only)

- Whisper — speech-to-text
- scikit-learn — crisis / distress classifier
- librosa — affective acoustic features
- Phi-3-mini (optional) — local generative replies
- FastAPI + Electron — packaging for Windows on Snapdragon

---

## Slide 7 — Safety & ethics

- Companion ≠ clinician
- Crisis detection routes to human helplines
- No self-harm instructions
- Transparent “on-device” status in UI

---

## Slide 8 — Ask / vision

Near term: ship portable `.exe` for HP Snapdragon laptops with Qualcomm AI Stack EP.  
Next: NPU-quantized Whisper + Phi-3 graphs, optional clinician dashboard that still keeps raw audio on-device.

**SoulCare makes private mental health AI practical — because Snapdragon runs it locally.**
