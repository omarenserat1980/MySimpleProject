"""Electronic Brain Cinema Engine V6 orchestration facade."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .brain_media_adapter import BrainMediaProvider
from .brain_review_loop import review_and_request
from .cinema_benchmark import benchmark_backend
from .cinema_timeline import build_timeline
from .model_router import ModelRouter


class CinemaEngineV6:
    def __init__(self) -> None:
        self.router = ModelRouter(BrainMediaProvider())

    def snapshot(self) -> dict[str, Any]:
        base = {
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
        base["brain_review"] = review_and_request(base)
        return base

    def render_shot(self, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        result = self.router.render(shot=shot, authorized=authorized)
        result["benchmark"] = benchmark_backend(result, shot)
        return result

    def export_timeline(self, shots: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
        return build_timeline(shots, output_path)
