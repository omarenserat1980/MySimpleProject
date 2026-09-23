"""Capability registry for measurable Electronic Brain growth.

Capabilities are claims backed by implementation status and evidence records.
The registry never grants operating permissions. The dependency graph adds a
second layer: it shows which safe capability can unlock the next economic step.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .self_development_engine import assess
from .capability_graph import graph_status, next_high_leverage

@dataclass(frozen=True)
class Capability:
    name: str
    domain: str
    status: str
    evidence_required: str

def registry() -> list[dict[str, Any]]:
    rows = []
    for row in assess()["domains"]:
        rows.append(asdict(Capability(
            name=row["name"],
            domain=row["category"],
            status=row["status"],
            evidence_required=row["evidence_required"],
        )))
    return rows

def capability_summary() -> dict[str, Any]:
    rows = registry()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    # Only explicitly mastered domains seed the dependency graph.
    mastered = {row["name"] for row in rows if row["status"] == "MASTERED"}
    frontier = graph_status(mastered)
    return {
        "counts": counts,
        "capabilities": rows,
        "dependency_frontier": frontier["capabilities"],
        "next_high_leverage": next_high_leverage(mastered),
    }
