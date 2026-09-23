"""Evidence-gated roadmap toward a 100,000 USD realized-revenue target.

The target is an objective, not a promise. The engine tracks only verified
payments and separates pipeline value from realized revenue. It can prioritize
legitimate work but cannot submit contracts, move money, or fabricate income.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

TARGET_USD = 100_000.0


@dataclass(frozen=True)
class RevenueOutcome:
    opportunity_id: str
    amount_usd: float
    status: str
    evidence: str = ""


@dataclass(frozen=True)
class RevenuePath:
    name: str
    mechanism: str
    automation_level: str
    external_action: str
    risk_notes: str


PATHS = (
    RevenuePath("service_factory", "repeatable digital services", "high",
                "client/platform submission", "demand and acquisition must be verified"),
    RevenuePath("productized_content", "reusable content packages", "high",
                "authorized storefront/marketplace", "sales are not guaranteed"),
    RevenuePath("video_factory", "short-form product/video production", "high",
                "authorized delivery channel", "rights and client requirements must be checked"),
    RevenuePath("software_microproduct", "small software products", "medium",
                "authorized marketplace/payment provider", "support and demand must be verified"),
    RevenuePath("local_commerce_support", "digital support for local businesses", "medium",
                "client-approved communication/payment", "commercial terms require owner approval"),
)


def verified_revenue(outcomes: Iterable[RevenueOutcome]) -> float:
    return round(sum(
        max(0.0, float(x.amount_usd))
        for x in outcomes
        if x.status.upper() in {"PAID", "VERIFIED_PAID", "SETTLED"}
        and x.evidence.strip()
    ), 2)


def target_status(outcomes: Iterable[RevenueOutcome]) -> dict:
    realized = verified_revenue(outcomes)
    remaining = max(0.0, TARGET_USD - realized)
    return {
        "target_usd": TARGET_USD,
        "verified_revenue_usd": realized,
        "remaining_usd": round(remaining, 2),
        "achieved": remaining == 0,
        "pipeline_is_not_revenue": True,
    }


def build_plan(outcomes: Iterable[RevenueOutcome] = ()) -> dict:
    status = target_status(outcomes)
    return {
        **status,
        "paths": [asdict(x) for x in PATHS],
        "priority_rule": "verified economics + evidence + speed + repeatability - risk",
        "next_action": (
            "VERIFY_AND_SCALE"
            if status["achieved"]
            else "FIND_AND_PREPARE_HIGHEST_EVIDENCE_OPPORTUNITY"
        ),
        "external_submission_performed": False,
        "money_movement_performed": False,
    }
