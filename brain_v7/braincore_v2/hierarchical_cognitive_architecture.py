"""Hierarchical cognitive architecture for Brain V7.

Adds multiple bounded reasoning layers: perception, belief, causal analysis,
strategy, planning, simulation, evaluation, and learning. It is intentionally
modular and deterministic so the brain can become more sophisticated without
creating uncontrolled self-modification or external side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping


def clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass(frozen=True)
class Signal:
    key: str
    value: float
    reliability: float = 0.5
    novelty: float = 0.5


@dataclass(frozen=True)
class Belief:
    key: str
    probability: float
    uncertainty: float
    evidence_count: int


@dataclass(frozen=True)
class CausalLink:
    cause: str
    effect: str
    strength: float
    confidence: float


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    objective: str
    expected_value: float
    risk: float
    reversibility: float


def perceive(signals: Iterable[Signal]) -> list[dict]:
    """Convert raw observations into bounded salience scores."""
    result = []
    for s in signals:
        salience = clamp(
            s.value * 0.35
            + s.reliability * 0.30
            + s.novelty * 0.20
            + (1.0 - s.reliability) * s.novelty * 0.15
        )
        result.append({
            "key": s.key,
            "salience": round(salience, 4),
            "reliability": round(clamp(s.reliability), 4),
            "novelty": round(clamp(s.novelty), 4),
        })
    return sorted(result, key=lambda x: x["salience"], reverse=True)


def infer_beliefs(
    signals: Iterable[Signal],
    prior: Mapping[str, float] | None = None,
) -> list[Belief]:
    priors = prior or {}
    beliefs = []
    for s in signals:
        p0 = clamp(priors.get(s.key, 0.5))
        reliability = clamp(s.reliability)
        posterior = p0 * (1.0 - reliability) + clamp(s.value) * reliability
        uncertainty = 1.0 - reliability
        beliefs.append(Belief(
            key=s.key,
            probability=round(posterior, 4),
            uncertainty=round(uncertainty, 4),
            evidence_count=1,
        ))
    return beliefs


def causal_analysis(
    beliefs: Iterable[Belief],
    links: Iterable[CausalLink],
) -> list[dict]:
    belief_map = {b.key: b for b in beliefs}
    result = []
    for link in links:
        cause = belief_map.get(link.cause)
        effect = belief_map.get(link.effect)
        if not cause or not effect:
            continue
        causal_confidence = clamp(
            link.strength * link.confidence
            * (1.0 - cause.uncertainty)
            * (1.0 - effect.uncertainty)
        )
        result.append({
            "cause": link.cause,
            "effect": link.effect,
            "causal_confidence": round(causal_confidence, 4),
            "expected_effect": round(
                clamp(effect.probability + link.strength * (cause.probability - 0.5)),
                4,
            ),
        })
    return sorted(result, key=lambda x: x["causal_confidence"], reverse=True)


def simulate_plan(
    steps: Iterable[PlanStep],
    *,
    uncertainty_penalty: float = 0.15,
) -> dict:
    rows = list(steps)
    if not rows:
        return {"status": "NO_PLAN", "expected_value": 0.0, "risk": 0.0}

    value = 1.0
    risk = 0.0
    reversibility = 0.0
    for step in rows:
        value *= 0.55 + 0.45 * clamp(step.expected_value)
        risk = 1.0 - (1.0 - risk) * (1.0 - clamp(step.risk))
        reversibility += clamp(step.reversibility)

    avg_rev = reversibility / len(rows)
    adjusted_value = clamp(value * (1.0 - uncertainty_penalty * risk))
    return {
        "status": "SIMULATED",
        "steps": len(rows),
        "expected_value": round(adjusted_value, 4),
        "risk": round(risk, 4),
        "average_reversibility": round(avg_rev, 4),
        "requires_external_execution": True,
        "simulation_only": True,
    }


def evaluate_alternatives(plans: Mapping[str, Mapping[str, float]]) -> list[dict]:
    """Compare plans without selecting or executing an irreversible action."""
    rows = []
    for name, p in plans.items():
        value = clamp(p.get("value", 0.0))
        risk = clamp(p.get("risk", 1.0))
        confidence = clamp(p.get("confidence", 0.0))
        reversibility = clamp(p.get("reversibility", 0.0))
        score = clamp(
            value * 0.40
            + confidence * 0.25
            + reversibility * 0.20
            + (1.0 - risk) * 0.15
        )
        rows.append({
            "plan": name,
            "score": round(score, 4),
            "value": value,
            "risk": risk,
            "confidence": confidence,
            "reversibility": reversibility,
        })
    return sorted(rows, key=lambda x: x["score"], reverse=True)


def cognitive_cycle(
    signals: Iterable[Signal],
    *,
    priors: Mapping[str, float] | None = None,
    causal_links: Iterable[CausalLink] = (),
    plans: Mapping[str, Mapping[str, float]] | None = None,
) -> dict:
    """Run one complete local perception→belief→causal→strategy cycle."""
    signal_list = list(signals)
    beliefs = infer_beliefs(signal_list, priors)
    perceived = perceive(signal_list)
    causal = causal_analysis(beliefs, causal_links)
    alternatives = evaluate_alternatives(plans or {})
    return {
        "architecture": "hierarchical_cognitive_v1",
        "layers": [
            "perception",
            "belief_inference",
            "causal_analysis",
            "strategy_evaluation",
            "simulation",
            "learning",
        ],
        "perception": perceived,
        "beliefs": [asdict(b) for b in beliefs],
        "causal_analysis": causal,
        "alternatives": alternatives,
        "next_phase": "learn_from_observed_outcome",
        "external_side_effects": False,
        "permission_escalation": False,
        "financial_execution": False,
    }


def architecture_snapshot() -> dict:
    return {
        "name": "Brain V7 Hierarchical Cognitive Architecture",
        "reasoning_depth": 6,
        "parallel_layers": 6,
        "self_modification": "bounded",
        "external_execution": "gated",
        "money_movement": "disabled_by_reasoning_layer",
        "design_principle": "compose_specialized bounded reasoning modules",
    }
