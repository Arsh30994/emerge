"""Backend utilities — Snapdragon acceleration + audio + benchmarks."""

from .snapdragon_optimization import SnapdragonRuntime, PerformanceMonitor
from .snapdragon_benchmarks import SnapdragonBenchmarks, AI_HUB_TARGETS
from .audio_preprocessing import load_audio_16k, TARGET_SR

__all__ = [
    "SnapdragonRuntime",
    "PerformanceMonitor",
    "SnapdragonBenchmarks",
    "AI_HUB_TARGETS",
    "load_audio_16k",
    "TARGET_SR",
]
