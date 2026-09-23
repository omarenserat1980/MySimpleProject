"""Capability registry for measurable Electronic Brain growth.

Capabilities are claims backed by implementation status and evidence records.
The registry never grants operating permissions.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .self_development_engine import assess

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
    return {"counts": counts, "capabilities": rows}
