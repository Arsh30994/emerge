# SoulCare Demo Script (≈5–7 minutes)

Audience: Snapdragon AI Lab judges.

## Setup (before you walk on stage)

1. Boot the HP Snapdragon laptop (or demo PC).
2. Terminal A:

```bash
cd soulcare-snapdragon/backend
..\.venv\Scripts\activate           # Windows
pip install -r requirements.txt     # first run only
python main.py
```

3. Terminal B:

```bash
cd soulcare-snapdragon/frontend
npm install                         # first run only
npm run dev:web
```

4. Open `http://127.0.0.1:5173` (or launch Electron with `npm run dev`).
5. Optional: open `http://127.0.0.1:8000/docs` for the live API.

---

## Opening (30s) — the problem

> “Students and workers need mental health support, but cloud chatbots send intimate data off-device. SoulCare keeps every word on this Snapdragon PC — private, offline-capable, low latency.”

Point to the UI pills: **Offline-capable · Privacy-first · Snapdragon**.

---

## Beat 1 — Text path (60s)

1. Type: `I've been stressed about deadlines and can't sleep.`
2. Hit **Send**.
3. Show **Risk pulse** moving to *moderate* / *high*.
4. Read the supportive reply.
5. Mention: TF-IDF + Logistic Regression ran in milliseconds on CPU.

---

## Beat 2 — Crisis safety (45s)

1. Type a crisis-indicating phrase (use carefully / briefly):  
   `I've been thinking about suicide and feel hopeless.`
2. Show **crisis** label + helpline banner (988 / IASP).
3. Emphasize: detection only — SoulCare is not a hotline; it routes to real help.

---

## Beat 3 — Voice path (90s)

1. Click **tap to talk**, speak: “Today was hard, I feel overwhelmed.”
2. Stop recording.
3. Walk the pipeline aloud:  
   **Whisper (local) → tone features → risk → reply**
4. If demo STT is on, say:  
   “Demo mode ships for instant judging; on this Snapdragon device we enable `FORCE_WHISPER=1` to run real Whisper on NPU/GPU.”

---

## Beat 4 — Snapdragon advantage (60s)

Open `http://127.0.0.1:8000/system` or `/metrics`:

- Preferred accelerator field (`npu` / `gpu` / `cpu`)
- Per-op latency samples

Say:

> “Whisper and Phi-3 target the Hexagon NPU / Adreno GPU via ONNX Runtime QNN or DirectML. The risk model stays on CPU because it’s tiny. Nothing crosses the network — that’s the Snapdragon story: private AI at the edge.”

---

## Beat 5 — Close (30s)

> “SoulCare = privacy-first mental health assistance that only Snapdragon-class local AI makes practical. Thank you.”

Hand judges: README, ARCHITECTURE.md, this script, pitch deck.

---

## Backup if mic / models fail

- Use text-only path (still shows risk + reply + metrics).
- `GET /classify` from Swagger for a 10-second classifier demo.
- Screenshot `/metrics` from a prior run.
