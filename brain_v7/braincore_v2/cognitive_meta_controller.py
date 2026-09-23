"""Deep meta-controller for Brain V7.

Combines adaptive priority signals, opportunity value, uncertainty and
capability gaps into an explainable development decision. The controller is
bounded and advisory: it does not grant permissions or perform external
side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping

from .adaptive_priority_engine import PrioritySignal, rank_signals


@dataclass(frozen=True)
class CognitiveDecision:
    domain: str
    objective: str
    priority: float
    confidence: float
    exploration: float
    exploitation: float
    reason: str


def _objective(domain: str, capability_gap: str | None) -> str:
    if capability_gap:
        return f"إغلاق فجوة القدرة في {domain}: {capability_gap}"
    return f"رفع قدرة {domain} لخدمة أعلى قيمة متاحة"


def decide(
    signals: Iterable[PrioritySignal],
    capability_gaps: Mapping[str, str] | None = None,
) -> dict:
    gaps = capability_gaps or {}
    ranked = rank_signals(signals)
    if not ranked:
        return {
            "status": "NO_SIGNAL",
            "decision": None,
            "next_action": "collect_more_observations",
        }

    top = ranked[0]
    gap = gaps.get(top["domain"])
    decision = CognitiveDecision(
        domain=top["domain"],
        objective=_objective(top["domain"], gap),
        priority=top["score"],
        confidence=top["confidence"],
        exploration=top["exploration_bonus"],
        exploitation=top["exploitation"],
        reason="highest_combined_adaptive_priority",
    )
    return {
        "status": "DECISION_READY",
        "decision": asdict(decision),
        "ranked_frontier": ranked,
        "next_action": "plan_bounded_local_change",
        "external_side_effects": False,
        "permission_escalation": False,
    }


def counterfactuals(
    signals: Iterable[PrioritySignal],
    *,
    confidence_penalty: float = 0.15,
) -> list[dict]:
    """Estimate how ranking changes if evidence confidence is discounted."""
    ranked = rank_signals(signals)
    results = []
    for item in ranked:
        adjusted = max(0.0, item["score"] - max(0.0, confidence_penalty) * (1 - item["confidence"]))
        results.append({
            "domain": item["domain"],
            "base_score": item["score"],
            "confidence": item["confidence"],
            "discounted_score": round(adjusted, 4),
        })
    return sorted(results, key=lambda x: x["discounted_score"], reverse=True)
