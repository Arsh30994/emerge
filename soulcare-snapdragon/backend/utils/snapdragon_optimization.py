"""
Snapdragon optimization helpers and performance monitoring.

Documents how SoulCare maps workloads onto Snapdragon X / X Elite
NPU, GPU (Adreno), and CPU for on-device inference.
"""

from __future__ import annotations

import logging
import os
import platform
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

logger = logging.getLogger("soulcare.perf")

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


@dataclass
class PerfSample:
    operation: str
    latency_ms: float
    memory_mb: float
    backend: str = "cpu"
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "latency_ms": round(self.latency_ms, 2),
            "memory_mb": round(self.memory_mb, 2),
            "backend": self.backend,
            **self.extra,
        }


class PerformanceMonitor:
    """Track latency and memory for hackathon benchmarking."""

    def __init__(self, max_samples: int = 200) -> None:
        self.samples: list[PerfSample] = []
        self.max_samples = max_samples

    def _memory_mb(self) -> float:
        if psutil is None:
            return 0.0
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)

    @contextmanager
    def track(self, operation: str, backend: str = "cpu") -> Generator[dict[str, Any], None, None]:
        extra: dict[str, Any] = {}
        start = time.perf_counter()
        mem_before = self._memory_mb()
        try:
            yield extra
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            mem_after = self._memory_mb()
            sample = PerfSample(
                operation=operation,
                latency_ms=elapsed_ms,
                memory_mb=max(mem_before, mem_after),
                backend=backend,
                extra=extra,
            )
            self.samples.append(sample)
            if len(self.samples) > self.max_samples:
                self.samples = self.samples[-self.max_samples :]
            logger.info(
                "perf op=%s latency_ms=%.1f memory_mb=%.1f backend=%s",
                operation,
                sample.latency_ms,
                sample.memory_mb,
                backend,
            )

    def summary(self) -> dict[str, Any]:
        if not self.samples:
            return {"count": 0, "samples": []}
        by_op: dict[str, list[float]] = {}
        for s in self.samples:
            by_op.setdefault(s.operation, []).append(s.latency_ms)
        averages = {
            op: round(sum(vals) / len(vals), 2) for op, vals in by_op.items()
        }
        return {
            "count": len(self.samples),
            "avg_latency_ms_by_op": averages,
            "recent": [s.as_dict() for s in self.samples[-20:]],
        }


class SnapdragonRuntime:
    """
    Detects preferred local acceleration path for Snapdragon HP PCs.

    Mapping (documented for judges — actual ONNX/QNN bindings depend on
    the OEM AI Stack installed on the device):

    | Workload              | Preferred unit | Stack idea                          |
    |-----------------------|----------------|-------------------------------------|
    | Whisper encode/decode | NPU / GPU      | ONNX Runtime + QNN EP / DirectML    |
    | TF-IDF + LogReg       | CPU            | sklearn (tiny; NPU overkill)        |
    | Tone (librosa)        | CPU / Hexagon  | numpy/scipy; optional DSP offload   |
    | Phi-3-mini (int4/int8)| NPU / GPU      | ONNX / ExecuTorch / DirectML        |

    Environment overrides:
      SOULCARE_ACCEL=npu|gpu|cpu
    """

    def __init__(self) -> None:
        self.preferred = os.getenv("SOULCARE_ACCEL", self._detect()).lower()
        self.info = self.describe()

    def _detect(self) -> str:
        # Best-effort detection; Snapdragon Windows devices often expose
        # Qualcomm AI Engine / DirectML adapters.
        machine = platform.machine().lower()
        proc = platform.processor().lower()
        if "qualcomm" in proc or "snapdragon" in proc or "arm" in machine:
            # Prefer NPU when Qualcomm AI Stack is present
            if os.path.exists(r"C:\Windows\System32\QnnHtp.dll") or os.getenv("QNN_SDK_ROOT"):
                return "npu"
            return "gpu"  # Adreno / DirectML fallback
        return "cpu"

    def describe(self) -> dict[str, Any]:
        return {
            "preferred_accelerator": self.preferred,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": platform.python_version(),
            "guidance": {
                "whisper": "Export Whisper to ONNX; run with ONNX Runtime QNN or DirectML EP on Snapdragon X Elite.",
                "risk_classifier": "Keep on CPU — sub-ms latency; models/risk_model.joblib.",
                "tone_analyzer": "CPU feature extract; optional Hexagon DSP for MFCC batches.",
                "phi3": "Use int4/int8 quantized Phi-3-mini via ONNX Runtime GenAI or ExecuTorch NPU kernels.",
            },
            "privacy": "All inference stays on-device; no cloud API calls.",
        }

    def backend_for(self, workload: str) -> str:
        mapping = {
            "stt": self.preferred if self.preferred in {"npu", "gpu"} else "cpu",
            "risk": "cpu",
            "tone": "cpu",
            "llm": self.preferred if self.preferred in {"npu", "gpu"} else "cpu",
        }
        return mapping.get(workload, "cpu")
