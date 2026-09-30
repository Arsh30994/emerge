"""
Snapdragon runtime detection + legacy PerformanceMonitor shim.

On Snapdragon X / X Elite HP PCs:
  - Whisper-Small / Distil-BERT / Phi-3.5 → NPU via ONNX Runtime QNN EP
  - Silero-VAD / librosa tone → CPU (tiny)
"""

from __future__ import annotations

import os
import platform
from typing import Any

from .snapdragon_benchmarks import SnapdragonBenchmarks

# Backward-compatible alias used by older imports
PerformanceMonitor = SnapdragonBenchmarks


class SnapdragonRuntime:
    def __init__(self) -> None:
        self.preferred = os.getenv("SOULCARE_ACCEL", self._detect()).lower()
        self.info = self.describe()

    def _detect(self) -> str:
        machine = platform.machine().lower()
        proc = platform.processor().lower()
        if "qualcomm" in proc or "snapdragon" in proc or "arm" in machine:
            if os.path.exists(r"C:\Windows\System32\QnnHtp.dll") or os.getenv("QNN_SDK_ROOT"):
                return "npu"
            return "gpu"
        return "cpu"

    def describe(self) -> dict[str, Any]:
        return {
            "preferred_accelerator": self.preferred,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "npu_tops_claim": 45,
            "guidance": {
                "whisper_small": (
                    "Fetch from AI Hub: qai-hub-models fetch Whisper-Small "
                    "--runtime qnn_context_binary — run via ONNX Runtime QNN EP."
                ),
                "distil_bert": (
                    "qai_hub_models.models.distil_bert_base_uncased_hf — "
                    "INT8/FP on NPU; ~100+ inf/sec target."
                ),
                "phi_3_5_mini": (
                    "qai_hub_models.models.phi_3_5_mini_instruct — "
                    "w4a16 QNN_CONTEXT_BINARY; ~42 tok/s on X Elite (device-dependent)."
                ),
                "silero_vad": "Keep on CPU — ~2MB, real-time speech gating.",
            },
            "privacy": "All inference stays on-device; no cloud API calls on Snapdragon builds.",
            "docs": {
                "ai_hub_models": "https://github.com/qualcomm/ai-hub-models",
                "ai_hub_apps": "https://github.com/qualcomm/ai-hub-apps",
                "workbench": "https://workbench.aihub.qualcomm.com/docs/",
            },
        }

    def backend_for(self, workload: str) -> str:
        mapping = {
            "stt": self.preferred if self.preferred in {"npu", "gpu"} else "cpu",
            "risk": self.preferred if self.preferred in {"npu", "gpu"} else "cpu",
            "tone": "cpu",
            "llm": self.preferred if self.preferred in {"npu", "gpu"} else "cpu",
        }
        return mapping.get(workload, "cpu")
