"""Bounded cognitive world model for Brain V7.

Maintains explicit hypotheses about capabilities and opportunities, updates
beliefs from observations, and produces competing plans. This is a local
reasoning layer; it does not grant permissions or execute external effects.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(frozen=True)
class Hypothesis:
    key: str
    claim: str
    belief: float = 0.5
    uncertainty: float = 0.5
    observations: int = 0
    supporting: int = 0
    contradicting: int = 0

    @property
    def confidence(self) -> float:
        evidence = self.supporting + self.contradicting
        if evidence == 0:
            return 0.0
        return self.supporting / evidence

    @property
    def information_gain_potential(self) -> float:
        return _clamp(self.uncertainty * (1.0 / (1.0 + self.observations)))


@dataclass(frozen=True)
class Observation:
    hypothesis_key: str
    outcome: float
    reliability: float = 1.0
    source: str = "local"


def update_belief(h: Hypothesis, observation: Observation) -> Hypothesis:
    reliability = _clamp(observation.reliability)
    outcome = _clamp(observation.outcome)
    alpha = 0.20 + 0.45 * reliability
    belief = h.belief * (1 - alpha) + outcome * alpha
    supporting = h.supporting + (1 if outcome >= 0.5 else 0)
    contradicting = h.contradicting + (1 if outcome < 0.5 else 0)
    evidence = supporting + contradicting
    uncertainty = 1.0 / (1.0 + evidence) 
    return Hypothesis(
        key=h.key,
        claim=h.claim,
        belief=_clamp(belief),
        uncertainty=_clamp(uncertainty),
        observations=h.observations + 1,
        supporting=supporting,
        contradicting=contradicting,
    )


def update_many(hypotheses: Iterable[Hypothesis],
                observations: Iterable[Observation]) -> list[Hypothesis]:
    table = {h.key: h for h in hypotheses}
    for obs in observations:
        if obs.hypothesis_key in table:
            table[obs.hypothesis_key] = update_belief(table[obs.hypothesis_key], obs)
    return list(table.values())


def rank_hypotheses(hypotheses: Iterable[Hypothesis]) -> list[dict]:
    rows = []
    for h in hypotheses:
        rows.append(asdict(h) | {
            "confidence": round(h.confidence, 4),
            "information_gain_potential": round(h.information_gain_potential, 4),
        })
    return sorted(rows, key=lambda x: (
        x["information_gain_potential"] * 0.45 + x["belief"] * 0.35 + x["confidence"] * 0.20
    ), reverse=True)


def generate_competing_plans(
    domain: str,
    *,
    belief: float,
    uncertainty: float,
    capability_gap: str = "",
) -> list[dict]:
    """Create competing bounded strategies instead of one fixed plan."""
    gap = capability_gap or "رفع القدرة الحالية"
    plans = [
        ("EXPLOIT", f"استثمار القدرة الحالية في {domain} لتحقيق {gap}", 0.72, 0.35),
        ("IMPROVE", f"تحسين نقطة الاختناق في {domain}: {gap}", 0.62, 0.45),
        ("EXPLORE", f"تجربة مسار جديد داخل {domain} لتقليل عدم اليقين", 0.48, 0.70),
        ("COMPOSE", f"تركيب {domain} مع قدرة أخرى لتوسيع الحل", 0.58, 0.60),
    ]
    scored = []
    for mode, objective, feasibility, information_gain in plans:
        score = (
            feasibility * 0.30
            + belief * 0.25
            + information_gain * uncertainty * 0.25
            + (1.0 - uncertainty) * 0.20
        )
        scored.append({
            "mode": mode,
            "objective": objective,
            "score": round(_clamp(score), 4),
            "information_gain": round(information_gain, 4),
        })
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def world_model_snapshot(
    hypotheses: Iterable[Hypothesis],
    capability_gaps: Mapping[str, str] | None = None,
) -> dict:
    ranked = rank_hypotheses(hypotheses)
    gaps = capability_gaps or {}
    return {
        "model_type": "bounded_belief_world_model",
        "hypotheses": ranked,
        "capability_gaps": dict(gaps),
        "next_mode": ranked[0]["key"] if ranked else None,
        "external_side_effects": False,
        "permission_escalation": False,
    }
