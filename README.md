# SoulCare Desktop (Snapdragon AI Lab)

Privacy-first on-device mental health assistant using **Qualcomm AI Hub** models
(Whisper-Small, Distil-BERT, Phi-3.5-Mini) on Snapdragon X Elite / X Plus.

## Start here

```bash
cd soulcare-snapdragon/backend
pip install -r requirements.txt
python main.py
```

```bash
cd soulcare-snapdragon/frontend
npm install
npm run dev:web
```

Full docs: [`soulcare-snapdragon/README.md`](./soulcare-snapdragon/README.md)  
Architecture: [`soulcare-snapdragon/ARCHITECTURE.md`](./soulcare-snapdragon/ARCHITECTURE.md)

AI Hub references:
- https://github.com/qualcomm/ai-hub-models
- https://github.com/qualcomm/ai-hub-apps
- https://workbench.aihub.qualcomm.com/docs/
