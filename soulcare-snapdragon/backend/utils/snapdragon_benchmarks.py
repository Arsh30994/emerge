"""
Snapdragon performance benchmarking helpers.

Targets (Qualcomm AI Hub published / cited for X Elite):
  - Whisper-Small: ~12.5× real-time transcription
  - Distil-BERT:   100+ inferences/sec
  - Phi-3.5-Mini:  ~42 tok/s (w4a16 on NPU; device-dependent)
  - End-to-end:    < 2 seconds
  - Memory:        ~2.5 GB working set with all models loaded
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

logger = logging.getLogger("soulcare.bench")

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


# Published / target figures for judge-facing docs & /benchmarks
AI_HUB_TARGETS = {
    "whisper_small": {
        "model_id": "qai_hub_models.models.whisper_small",
        "size_mb": 244,
        "realtime_factor": 12.5,
        "target_latency_ms": 100,
        "runtime": "ONNX Runtime + QNN EP",
    },
    "silero_vad": {
        "model_id": "silero-vad",
        "size_mb": 2,
        "target_latency_ms": 10,
        "runtime": "CPU (real-time)",
    },
    "distil_bert": {
        "model_id": "qai_hub_models.models.distil_bert_base_uncased_hf",
        "size_mb": 67,
        "inferences_per_sec": 100,
        "target_latency_ms": 50,
        "runtime": "ONNX Runtime + QNN EP",
    },
    "phi_3_5_mini": {
        "model_id": "qai_hub_models.models.phi_3_5_mini_instruct",
        "size_mb": 2100,
        "tokens_per_sec": 42,
        "runtime": "QNN_CONTEXT_BINARY w4a16 / llama.cpp",
        "npu_tops": 45,
    },
    "system": {
        "e2e_target_s": 2.0,
        "memory_target_gb": 2.5,
        "npu_tops_snapdragon_x_elite": 45,
        "npu_tops_apple_m3": 18,
    },
}


@dataclass
class BenchSample:
    operation: str
    latency_ms: float
    memory_mb: float
    backend: str = "cpu"
    tokens: int | None = None
    tokens_per_sec: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "operation": self.operation,
            "latency_ms": round(self.latency_ms, 2),
            "memory_mb": round(self.memory_mb, 2),
            "backend": self.backend,
        }
        if self.tokens is not None:
            d["tokens"] = self.tokens
        if self.tokens_per_sec is not None:
            d["tokens_per_sec"] = round(self.tokens_per_sec, 2)
        d.update(self.extra)
        return d


class SnapdragonBenchmarks:
    """Collect latency / memory / tok/s for hackathon judging."""

    def __init__(self, max_samples: int = 300) -> None:
        self.samples: list[BenchSample] = []
        self.max_samples = max_samples
        self.targets = AI_HUB_TARGETS

    def _memory_mb(self) -> float:
        if psutil is None:
            return 0.0
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)

    @contextmanager
    def track(
        self,
        operation: str,
        backend: str = "cpu",
        tokens: int | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        extra: dict[str, Any] = {}
        start = time.perf_counter()
        mem_before = self._memory_mb()
        try:
            yield extra
        finally:
            elapsed = time.perf_counter() - start
            elapsed_ms = elapsed * 1000
            tok_count = extra.get("tokens", tokens)
            tps = None
            if tok_count and elapsed > 0:
                tps = float(tok_count) / elapsed
            sample = BenchSample(
                operation=operation,
                latency_ms=elapsed_ms,
                memory_mb=max(mem_before, self._memory_mb()),
                backend=backend,
                tokens=tok_count,
                tokens_per_sec=tps,
                extra={k: v for k, v in extra.items() if k != "tokens"},
            )
            self.samples.append(sample)
            if len(self.samples) > self.max_samples:
                self.samples = self.samples[-self.max_samples :]
            logger.info(
                "bench op=%s latency_ms=%.1f mem_mb=%.1f backend=%s tps=%s",
                operation,
                sample.latency_ms,
                sample.memory_mb,
                backend,
                f"{tps:.1f}" if tps else "-",
            )

    def summary(self) -> dict[str, Any]:
        by_op: dict[str, list[float]] = {}
        for s in self.samples:
            by_op.setdefault(s.operation, []).append(s.latency_ms)
        averages = {op: round(sum(v) / len(v), 2) for op, v in by_op.items()}
        return {
            "count": len(self.samples),
            "avg_latency_ms_by_op": averages,
            "targets": self.targets,
            "recent": [s.as_dict() for s in self.samples[-25:]],
            "meets_e2e_target": self._e2e_ok(averages),
        }

    def _e2e_ok(self, averages: dict[str, float]) -> bool | None:
        e2e = averages.get("voice_chat_total") or averages.get("chat_total")
        if e2e is None:
            return None
        return e2e < self.targets["system"]["e2e_target_s"] * 1000
