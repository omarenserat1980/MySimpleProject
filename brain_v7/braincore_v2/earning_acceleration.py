"""Earning acceleration layer.

Turns discovered leads into an evidence-first execution queue.
It never sends proposals, moves money, or claims income by itself.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import time
from typing import Any, Iterable


@dataclass(frozen=True)
class EarningCandidate:
    lead_id: str
    title: str
    service: str
    offered_jod: float
    effort_hours: float
    fit: float
    evidence: float
    friction: float
    risk: float

    @property
    def expected_hourly_jod(self) -> float:
        return self.offered_jod / max(self.effort_hours, 0.1)

    @property
    def score(self) -> float:
        # Bounded score: economics + fit/evidence, penalized by friction/risk.
        return round(
            (self.expected_hourly_jod * 0.45)
            + (self.fit * 25.0)
            + (self.evidence * 20.0)
            - (self.friction * 15.0)
            - (self.risk * 25.0),
            3,
        )


def candidate_from_lead(lead: dict[str, Any]) -> EarningCandidate | None:
    try:
        offered = float(lead.get("offered_jod"))
        hours = float(lead.get("effort_hours", 1.0))
        fit = float(lead.get("fit", 0.5))
        evidence = float(lead.get("evidence", 0.5))
        friction = float(lead.get("friction", 0.5))
        risk = float(lead.get("risk", 0.0))
    except (TypeError, ValueError):
        return None
    if not lead.get("lead_id") or not lead.get("title") or offered <= 0 or hours <= 0:
        return None
    if not all(0.0 <= x <= 1.0 for x in (fit, evidence, friction, risk)):
        return None
    return EarningCandidate(
        lead_id=str(lead["lead_id"]),
        title=str(lead["title"]),
        service=str(lead.get("service", "")),
        offered_jod=offered,
        effort_hours=hours,
        fit=fit,
        evidence=evidence,
        friction=friction,
        risk=risk,
    )


def rank_candidates(leads: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [candidate_from_lead(x) for x in leads]
    candidates = [x for x in candidates if x is not None]
    return [asdict(x) | {"expected_hourly_jod": x.expected_hourly_jod, "score": x.score}
            for x in sorted(candidates, key=lambda x: x.score, reverse=True)]


def proposal_for(candidate: dict[str, Any]) -> str:
    service = str(candidate.get("service", "service"))
    return (
        "Hello,\\n\\n"
        f"I can deliver the requested {service} in Arabic with a clear, "
        "professional, platform-ready result. I can start immediately, "
        "follow your brief, and provide a concise revision cycle.\\n\\n"
        "I can share a relevant sample and confirm the exact deliverables "
        "before starting.\\n\\nBest regards"
    )


def execution_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence = float(candidate.get("evidence", 0.0))
    fit = float(candidate.get("fit", 0.0))
    risk = float(candidate.get("risk", 1.0))
    if evidence < 0.6:
        return {"status": "RESEARCH_REQUIRED", "reason": "INSUFFICIENT_EVIDENCE"}
    if fit < 0.5:
        return {"status": "LOW_FIT", "reason": "SKILL_FIT_TOO_LOW"}
    if risk > 0.5:
        return {"status": "REVIEW_REQUIRED", "reason": "RISK_TOO_HIGH"}
    return {
        "status": "READY_FOR_USER_SUBMISSION",
        "reason": "EVIDENCE_AND_FIT_SUFFICIENT",
        "requires_user_submission": True,
    }


def batch_report(leads: Iterable[dict[str, Any]]) -> dict[str, Any]:
    ranked = rank_candidates(leads)
    return {
        "generated_at": time.time(),
        "candidate_count": len(ranked),
        "candidates": ranked,
        "realized_profit_jod": 0.0,
        "profit_status": "NO_VERIFIED_PAYMENT",
        "money_movement_authorized": False,
    }
