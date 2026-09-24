"""Capability graph: turn skills into measurable, dependency-aware development paths.

The graph never grants permissions. It only computes what capability is missing,
what evidence is required, and which safe improvement has the highest leverage.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class Capability:
    name: str
    depends_on: tuple[str, ...] = ()
    evidence: str = "tests + observable evidence"
    value_weight: float = 1.0

CAPABILITIES = (
    Capability("software_tests", (), "passing regression tests", 1.0),
    Capability("data_validation", ("software_tests",), "validation tests", 1.2),
    Capability("research", ("data_validation",), "source-backed observations", 1.4),
    Capability("opportunity_discovery", ("research",), "real sourced opportunities", 2.0),
    Capability("service_delivery", ("software_tests",), "successful artifact verification", 2.0),
    Capability("lead_to_payment", ("opportunity_discovery", "service_delivery"), "verified paid ledger entry", 3.0),
    Capability("autonomous_optimization", ("lead_to_payment",), "repeatable measured improvement", 3.0),
)

def _index() -> dict[str, Capability]:
    return {c.name: c for c in CAPABILITIES}

def graph_status(mastered: set[str] | None = None) -> dict[str, Any]:
    mastered = set(mastered or set())
    idx = _index()
    rows=[]
    for c in CAPABILITIES:
        missing=[d for d in c.depends_on if d not in mastered]
        rows.append({**asdict(c), "ready": not missing and c.name not in mastered,
                     "missing_dependencies": missing,
                     "status": "MASTERED" if c.name in mastered else ("READY" if not missing else "BLOCKED")})
    return {"capabilities": rows, "mastered": sorted(mastered)}

def next_high_leverage(mastered: set[str] | None = None) -> dict[str, Any] | None:
    rows=graph_status(mastered)["capabilities"]
    ready=[r for r in rows if r["ready"]]
    if not ready:
        return None
    ready_names = {r["name"] for r in ready}
    return next((r for r in rows if r["name"] in ready_names and r["ready"] and float(r["value_weight"]) == max(float(x["value_weight"]) for x in ready)), None)

def learning_frontier(mastered: set[str] | None = None) -> list[dict[str, Any]]:
    return [r for r in graph_status(mastered)["capabilities"] if r["status"] in {"READY","BLOCKED"}]
