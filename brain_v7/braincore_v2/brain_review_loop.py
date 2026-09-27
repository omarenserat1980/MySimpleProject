"""Autonomous Brain review loop for Cinema Engine V6.

This is the factory's internal proposal -> review -> request -> implementation
contract. It does not pretend that a second human/agent exists; the review is
deterministic and auditable.
"""
from __future__ import annotations

from typing import Any

from .open_source_cinema_catalog import integration_plan


def propose(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    if not snapshot.get("router", {}).get("comfyui_configured"):
        requests.append({"id": "COMFYUI_CONNECTOR", "priority": 100, "reason": "enable local/remote open workflow execution"})
    requests.append({"id": "CONTINUITY_FIRST", "priority": 95, "reason": "lock character/world references before expensive video generation"})
    requests.append({"id": "AUDIO_FIRST", "priority": 90, "reason": "make duration and dialogue timing first-class inputs"})
    requests.append({"id": "SHOT_BENCHMARK", "priority": 85, "reason": "compare backend output using the same shot contract"})
    requests.append({"id": "TIMELINE_HANDOFF", "priority": 80, "reason": "keep edit decisions independent of the renderer"})
    return requests


def review_and_request(snapshot: dict[str, Any]) -> dict[str, Any]:
    proposals = propose(snapshot)
    implemented = {
        "CONTINUITY_FIRST": True,
        "AUDIO_FIRST": True,
        "SHOT_BENCHMARK": True,
        "TIMELINE_HANDOFF": True,
        "COMFYUI_CONNECTOR": bool(snapshot.get("router", {}).get("comfyui_configured")),
    }
    remaining = [p for p in proposals if not implemented.get(p["id"], False)]
    return {
        "status": "READY" if not remaining else "DEGRADED",
        "proposals": proposals,
        "implemented": implemented,
        "remaining_requests": remaining,
        "next_policy": integration_plan(),
    }
