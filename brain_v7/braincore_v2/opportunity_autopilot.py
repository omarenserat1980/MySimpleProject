"""Opportunity Autopilot.

Converts discovered opportunities into bounded, evidence-gated execution plans.
It can prepare work autonomously but never impersonates the owner, bypasses
provider controls, submits unsolicited applications, or claims payment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable
import hashlib
import time


@dataclass(frozen=True)
class OpportunityPlan:
    opportunity_id: str
    title: str
    service: str
    value_jod: float
    effort_hours: float
    freshness_hours: float
    evidence_score: float
    fit_score: float
    risk_score: float
    local_execution: bool
    api_delivery_possible: bool

    @property
    def speed_value(self) -> float:
        effort = max(self.effort_hours, 0.1)
        return max(self.value_jod, 0.0) / effort

    @property
    def priority(self) -> float:
        freshness = max(0.0, min(1.0, 1.0 - self.freshness_hours / 168.0))
        evidence = max(0.0, min(1.0, self.evidence_score))
        fit = max(0.0, min(1.0, self.fit_score))
        risk = max(0.0, min(1.0, self.risk_score))
        return (
            self.speed_value * 0.35
            + evidence * 30
            + fit * 20
            + freshness * 10
            - risk * 25
        )


def stable_id(title: str, url: str = "") -> str:
    raw = (title.strip() + "|" + url.strip()).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def plan_from_lead(lead: dict[str, Any]) -> OpportunityPlan:
    title = str(lead.get("title", "")).strip()
    url = str(lead.get("url", "")).strip()
    return OpportunityPlan(
        opportunity_id=str(lead.get("lead_id") or stable_id(title, url)),
        title=title,
        service=str(lead.get("service", "")),
        value_jod=float(lead.get("offered_jod") or 0),
        effort_hours=max(float(lead.get("effort_hours") or 1), 0.1),
        freshness_hours=max(float(lead.get("freshness_hours") or 0), 0),
        evidence_score=max(0, min(1, float(lead.get("evidence_score", 0)))),
        fit_score=max(0, min(1, float(lead.get("fit_score", 0)))),
        risk_score=max(0, min(1, float(lead.get("risk_score", 1)))),
        local_execution=bool(lead.get("local_execution", True)),
        api_delivery_possible=bool(lead.get("api_delivery_possible", False)),
    )


def rank(plans: Iterable[OpportunityPlan]) -> list[dict[str, Any]]:
    rows = sorted(plans, key=lambda p: p.priority, reverse=True)
    return [
        {
            **asdict(p),
            "speed_value_jod_per_hour": round(p.speed_value, 2),
            "priority": round(p.priority, 2),
        }
        for p in rows
    ]


def execution_gate(
    plan: OpportunityPlan,
    *,
    artifact_ready: bool = False,
    external_authorized: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not plan.local_execution:
        blockers.append("LOCAL_EXECUTION_UNAVAILABLE")
    if plan.evidence_score < 0.6:
        blockers.append("INSUFFICIENT_EVIDENCE")
    if plan.fit_score < 0.5:
        blockers.append("LOW_FIT")
    if plan.risk_score > 0.5:
        blockers.append("RISK_REVIEW_REQUIRED")
    if not artifact_ready:
        blockers.append("ARTIFACT_NOT_READY")

    can_prepare = not any(
        x in blockers
        for x in (
            "LOCAL_EXECUTION_UNAVAILABLE",
            "INSUFFICIENT_EVIDENCE",
            "LOW_FIT",
            "RISK_REVIEW_REQUIRED",
        )
    )

    can_submit = can_prepare and artifact_ready and external_authorized and (
        plan.api_delivery_possible
    )

    return {
        "status": (
            "READY_FOR_AUTHORIZED_API_SUBMISSION"
            if can_submit
            else "READY_TO_PREPARE" if can_prepare else "BLOCKED"
        ),
        "blockers": blockers,
        "artifact_ready": artifact_ready,
        "external_authorized": external_authorized,
        "submission_performed": False,
        "payment_verified": False,
        "income_claim_allowed": False,
    }


def autopilot_snapshot(
    leads: Iterable[dict[str, Any]],
    *,
    artifact_ready_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Build a bounded execution queue without performing external side effects."""
    artifact_ready_ids = artifact_ready_ids or set()
    plans = [plan_from_lead(x) for x in leads]
    ranked = rank(plans)
    gates = []
    for p in plans:
        gates.append(
            execution_gate(
                p,
                artifact_ready=p.opportunity_id in artifact_ready_ids,
                external_authorized=False,
            )
        )
    return {
        "generated_at": int(time.time()),
        "candidate_count": len(plans),
        "ranked": ranked,
        "gates": gates,
        "external_side_effects_performed": False,
        "realized_profit_jod": 0.0,
        "profit_status": "NO_VERIFIED_PAYMENT",
    }
