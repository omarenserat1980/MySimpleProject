"""Cinematic Money Factory: economic control layer for the video factory.

It chooses production targets using expected value, effort, evidence and
learning value. It never invents revenue, moves money or publishes externally.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ContentOpportunity:
    title: str
    objective: str
    expected_value_jod: float
    effort_hours: float
    evidence: float
    repeatability: float
    risk: float
    freshness: float
    route: str


def score(o: ContentOpportunity) -> float:
    effort = max(0.25, o.effort_hours)
    hourly = max(0.0, o.expected_value_jod) / effort
    return (
        0.32 * min(hourly / 100.0, 1.0)
        + 0.18 * max(0.0, min(o.evidence, 1.0))
        + 0.18 * max(0.0, min(o.repeatability, 1.0))
        + 0.12 * max(0.0, min(o.freshness, 1.0))
        + 0.10 * max(0.0, min(o.risk, 1.0)) * -1.0
        + 0.10
    )


def rank(items: list[ContentOpportunity]) -> list[dict[str, Any]]:
    return sorted(
        [{"opportunity": asdict(x), "score": score(x)} for x in items],
        key=lambda x: x["score"], reverse=True,
    )


def build_factory_plan(objective: str, opportunities: list[ContentOpportunity] | None = None) -> dict[str, Any]:
    candidates = opportunities or [
        ContentOpportunity(
            title="Evergreen cinematic educational video",
            objective=objective,
            expected_value_jod=25.0,
            effort_hours=2.0,
            evidence=0.5,
            repeatability=0.9,
            risk=0.2,
            freshness=0.8,
            route="youtube",
        )
    ]
    ranked = rank(candidates)
    return {
        "factory": "CINEMATIC_MONEY_FACTORY",
        "selected": ranked[0] if ranked else None,
        "queue": ranked,
        "economic_status": "PLANNING_ONLY",
        "realized_profit_jod": 0.0,
        "profit_status": "NO_VERIFIED_PAYMENT",
        "next_measurement": (
            "After publication, ingest verified analytics and payment data; "
            "never infer revenue from views alone."
        ),
    }


def snapshot() -> dict[str, Any]:
    return {
        "economic_selection": True,
        "speed_value_tradeoff": True,
        "verified_revenue_only": True,
        "youtube_route": True,
        "external_submission": "permission_gated",
        "money_movement": False,
    }
