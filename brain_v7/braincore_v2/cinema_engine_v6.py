"""Electronic Brain Cinema Engine V6 orchestration facade.

This module exposes the new cinema stack as one capability surface while
keeping the existing factory controller as the authoritative production loop.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .brain_media_adapter import BrainMediaProvider
from .cinema_benchmark import benchmark_backend
from .cinema_timeline import build_timeline
from .model_router import ModelRouter


class CinemaEngineV6:
    def __init__(self) -> None:
        self.router = ModelRouter(BrainMediaProvider())

    def snapshot(self) -> dict[str, Any]:
        return {
            "engine": "Electronic Brain Cinema Engine V6",
            "version": 6,
            "router": self.router.snapshot(),
            "capabilities": [
                "ComfyUI",
                "Wan/LTX/Hunyuan workflow profiles",
                "model routing",
                "character/world continuity",
                "visual/audio/research QC",
                "OpenTimelineIO export",
                "resume/retry",
                "persistent memory",
            ],
        }

    def render_shot(self, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        result = self.router.render(shot=shot, authorized=authorized)
        result["benchmark"] = benchmark_backend(result, shot)
        return result

    def export_timeline(self, shots: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
        return build_timeline(shots, output_path)
