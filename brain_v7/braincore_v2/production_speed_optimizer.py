"""Planning layer for verified throughput optimizations.

It never lowers QC thresholds. It only identifies safe opportunities for
parallelism, batching and speculative work; actual backend support is required
before a capability is activated.
"""
from __future__ import annotations
from collections import defaultdict
from typing import Any

def speed_plan(shots: list[dict[str, Any]], max_concurrency: int = 8) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for shot in shots:
        generation = shot.get("generation") or {}
        key = (
            str(shot.get("model_family") or generation.get("backend_preference") or "auto"),
            int(shot.get("width") or generation.get("width") or 0),
            int(shot.get("height") or generation.get("height") or 0),
            int(shot.get("frames") or generation.get("frames") or 0),
            int(shot.get("duration_s") or 0),
        )
        groups[key].append(str(shot.get("shot_id", "")))
    return {
        "max_concurrency": max(1, min(8, int(max_concurrency))),
        "batch_groups": [
            {"key": list(key), "shot_ids": ids, "batch_eligible": len(ids) > 1}
            for key, ids in groups.items()
        ],
        "warm_model_cache": True,
        "reference_cache": True,
        "pipeline_overlap": True,
        "speculative_generation": "qc_gated",
        "quality_floor_unchanged": True,
    }

def speculative_budget(shot: dict[str, Any]) -> int:
    generation = shot.get("generation") or {}
    policy = str(generation.get("continuity_policy") or "")
    purpose = str(shot.get("purpose") or "").lower()
    if "identity" in policy or "match_cut" in policy or any(x in purpose for x in ("hero", "dialogue", "action")):
        return 2
    return 1
