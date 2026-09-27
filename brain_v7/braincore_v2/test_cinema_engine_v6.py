from __future__ import annotations

import os

from .cinema_benchmark import benchmark_backend
from .cinema_timeline import build_timeline
from .model_router import ModelRouter


class _Fallback:
    def render(self, *, shot, authorized=False):
        return {"status": "VERIFIED_COMPLETED", "video_ref": "memory://shot.mp4", "router": {"selected": "fallback"}}


def test_router_falls_back_without_comfyui():
    old = os.environ.pop("COMFYUI_URL", None)
    old_workflow = os.environ.pop("COMFYUI_WORKFLOW_JSON", None)
    try:
        router = ModelRouter(_Fallback())
        result = router.render(
            shot={"shot_id": "shot_0001", "visual_prompt": "cinematic", "continuity_key": "c1"},
            authorized=True,
        )
        assert result["status"] == "VERIFIED_COMPLETED"
        assert result["router"]["fallback_used"] is True
    finally:
        if old is not None:
            os.environ["COMFYUI_URL"] = old
        if old_workflow is not None:
            os.environ["COMFYUI_WORKFLOW_JSON"] = old_workflow


def test_benchmark_requires_media_and_contract():
    result = benchmark_backend(
        {"status": "VERIFIED_COMPLETED", "video_ref": "x", "router": {"selected": "fallback"}},
        {"shot_id": "s", "visual_prompt": "x", "continuity_key": "c"},
    )
    assert result["status"] == "PASS"


def test_timeline_fallback(tmp_path):
    result = build_timeline([{"shot_id": "s", "video_ref": "x", "duration_s": 2}], tmp_path / "timeline.otio")
    assert result["clips"] == 1
