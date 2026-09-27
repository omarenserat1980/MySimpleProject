"""Deterministic capability/continuity benchmark for cinema backends."""
from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = ("shot_id", "visual_prompt", "continuity_key")


def benchmark_backend(result: dict[str, Any], shot: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "provider_completed": result.get("status") in {"COMPLETED", "VERIFIED_COMPLETED"},
        "has_video": bool(result.get("video_ref")),
        "shot_contract": all(bool(shot.get(k)) for k in REQUIRED_FIELDS),
        "vision_qc": bool(result.get("vision_qc")),
        "router_recorded": bool(result.get("router")),
    }
    passed = sum(1 for value in checks.values() if value)
    score = passed / len(checks)
    return {
        "status": "PASS" if score >= 0.8 else "FAIL",
        "score": score,
        "checks": checks,
        "required_threshold": 0.8,
    }
