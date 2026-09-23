"""Evidence-first global opportunity scanner.

This module ranks a market/product pair only from supplied observations.
It does not fetch the web and never invents live demand or prices.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class OpportunityEvidence:
    market: str
    product: str
    price_jod: float | None
    landed_cost_jod: float | None
    demand_score: float | None
    competition_score: float | None
    evidence_count: int = 0
    verified: bool = False

def evaluate(e: OpportunityEvidence) -> dict[str, Any]:
    missing=[]
    for name,value in (
        ("price_jod",e.price_jod),("landed_cost_jod",e.landed_cost_jod),
        ("demand_score",e.demand_score),("competition_score",e.competition_score)):
        if value is None: missing.append(name)
    if missing:
        return {"status":"NEEDS_RESEARCH","market":e.market,"product":e.product,
                "missing":missing,"decision":"NO_BUY_DECISION"}
    profit=e.price_jod-e.landed_cost_jod
    margin=profit/e.price_jod if e.price_jod else 0
    # Scores are descriptive, not predictions. Evidence quality gates the result.
    evidence_quality=min(1.0,e.evidence_count/3)
    return {"status":"EVIDENCE_READY" if e.verified and evidence_quality>=1 else "UNVERIFIED",
            "market":e.market,"product":e.product,
            "gross_profit_jod":round(profit,2),"gross_margin":round(margin,4),
            "demand_score":e.demand_score,"competition_score":e.competition_score,
            "evidence_quality":round(evidence_quality,2),
            "decision":"REVIEW_REQUIRED"}

def batch_evaluate(items:list[OpportunityEvidence]) -> list[dict[str,Any]]:
    return [evaluate(x) for x in items]
