"""Evidence-first planner for evaluating Global AI Radar adapters.

This module creates an evaluation plan from registry metadata. It does not claim
that a backend passed a benchmark, security test, or license review. Those
stages require independent executors and recorded evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "global_ai_radar.json"

STAGES = (
    "discover",
    "license_check",
    "capability_test",
    "security_test",
    "benchmark",
    "evidence_review",
    "adapter_validation",
    "verify",
)


@dataclass(frozen=True)
class Stage:
    name: str
    status: str = "PENDING"
    evidence_required: bool = True


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0":
        raise ValueError("unsupported radar schema")
    if not data.get("selection_policy", {}).get("independent_verification_required"):
        raise ValueError("independent verification must remain enabled")
    return data


def build_plan(item: dict[str, Any]) -> dict[str, Any]:
    if not item.get("id") or not item.get("source") or not item.get("why_add"):
        raise ValueError("registry item is missing required evidence metadata")

    return {
        "backend_id": item["id"],
        "source": item["source"],
        "region": item.get("region"),
        "category": item.get("category"),
        "role": item.get("role"),
        "status": item.get("status", "candidate"),
        "stages": [asdict(Stage(name=stage)) for stage in STAGES],
        "promotion_rule": (
            "PROMOTE only when every required stage has independent evidence; "
            "a process exit code alone is never sufficient."
        ),
    }


def build_all_plans(data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    registry = data or load_registry()
    return [build_plan(item) for item in registry["recommended"]]


def summarize(plans: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "candidates": len(plans),
        "stages_per_candidate": len(STAGES),
        "pending_evidence_stages": sum(len(p["stages"]) for p in plans),
        "promotable": 0,
    }


if __name__ == "__main__":
    plans = build_all_plans()
    print(json.dumps(summarize(plans), ensure_ascii=False, indent=2))
