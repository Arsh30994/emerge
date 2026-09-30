#!/usr/bin/env bash
# Fetch Qualcomm AI Hub deployable assets for SoulCare (run on Windows/Snapdragon).
# Requires: pip install qai_hub_models_cli
# Docs: https://workbench.aihub.qualcomm.com/docs/
set -euo pipefail
OUT="${1:-../models}"
mkdir -p "$OUT"
echo "Fetching Whisper-Small..."
qai-hub-models fetch Whisper-Small --runtime qnn_context_binary --precision float || true
echo "Fetching Distil-Bert-Base-Uncased-Hf..."
qai-hub-models fetch Distil-Bert-Base-Uncased-Hf --runtime qnn_context_binary || true
echo "Fetching Phi-3.5-Mini-Instruct..."
qai-hub-models fetch Phi-3.5-Mini-Instruct --runtime qnn_context_binary --precision w4a16 || true
echo "Done. Place downloaded assets under $OUT and set SOULCARE_DEMO=0 SOULCARE_ACCEL=npu"
