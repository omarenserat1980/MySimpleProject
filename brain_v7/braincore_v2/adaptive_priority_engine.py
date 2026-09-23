"""Adaptive cognitive priority engine.

Maintains a bounded, explainable feedback model for deciding what the brain
should develop next. It combines opportunity economics, execution speed,
observed outcomes, repeatability, uncertainty, freshness and exploration.
It is decision support only: it never grants permissions or performs external
side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import log, sqrt, log1p
from typing import Iterable, Sequence


@dataclass(frozen=True)
class PrioritySignal:
    domain: str
    opportunity_value: float = 0.0
    speed: float = 0.0
    outcome: float = 0.0
    repeatability: float = 0.0
    evidence: float = 0.0
    freshness: float = 1.0
    uncertainty: float = 1.0
    attempts: int = 0
    failures: int = 0

    @property
    def exploitation(self) -> float:
        return (
            max(0.0, self.opportunity_value) * 0.28
            + max(0.0, self.speed) * 0.14
            + max(0.0, self.outcome) * 0.24
            + max(0.0, self.repeatability) * 0.12
            + max(0.0, self.evidence) * 0.12
            + max(0.0, self.freshness) * 0.10
        )

    @property
    def exploration_bonus(self) -> float:
        attempts = max(1, self.attempts)
        uncertainty = max(0.0, min(1.0, self.uncertainty))
        failure_rate = self.failures / attempts
        return min(0.25, 0.10 * uncertainty + 0.08 / sqrt(attempts)
                    + 0.07 * (1 - failure_rate))

    @property
    def score(self) -> float:
        return max(0.0, self.exploitation * (0.65 + 0.35 * self.freshness)
                    + self.exploration_bonus)

    @property
    def confidence(self) -> float:
        return max(0.0, min(1.0, self.evidence * (1.0 - self.uncertainty)
                              + min(1.0, self.attempts / 5.0) * 0.35))


def _merge(signals: Sequence[PrioritySignal]) -> list[PrioritySignal]:
    grouped: dict[str, list[PrioritySignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.domain, []).append(signal)
    merged: list[PrioritySignal] = []
    for domain, items in grouped.items():
        weights = [1.0 / (i + 1) for i in range(len(items))]
        total = sum(weights)
        def avg(field: str) -> float:
            return sum(getattr(x, field) * w for x, w in zip(items, weights)) / total
        merged.append(PrioritySignal(
            domain=domain,
            opportunity_value=avg("opportunity_value"),
            speed=avg("speed"),
            outcome=avg("outcome"),
            repeatability=avg("repeatability"),
            evidence=avg("evidence"),
            freshness=avg("freshness"),
            uncertainty=avg("uncertainty"),
            attempts=sum(x.attempts for x in items),
            failures=sum(x.failures for x in items),
        ))
    return merged


def rank_signals(signals: Iterable[PrioritySignal]) -> list[dict]:
    ranked = sorted(_merge(list(signals)), key=lambda x: x.score, reverse=True)
    return [
        asdict(s) | {
            "exploitation": round(s.exploitation, 4),
            "exploration_bonus": round(s.exploration_bonus, 4),
            "score": round(s.score, 4),
            "confidence": round(s.confidence, 4),
        }
        for s in ranked
    ]


def next_focus(signals: Iterable[PrioritySignal], *, fallback_domain: str = "software_engineering") -> dict:
    ranked = rank_signals(signals)
    if not ranked:
        return {"domain": fallback_domain, "reason": "NO_FEEDBACK", "ranked": []}
    best = ranked[0]
    return {
        "domain": best["domain"],
        "reason": "ADAPTIVE_EXPLOIT_EXPLORE",
        "score": best["score"],
        "confidence": best["confidence"],
        "ranked": ranked,
    }


def feedback_from_cycle(domain: str, *, opportunity_value: float = 0.0,
                        speed: float = 0.0, outcome: float = 0.0,
                        repeatability: float = 0.0, evidence: float = 0.0,
                        freshness: float = 1.0, uncertainty: float = 1.0,
                        attempts: int = 0, failures: int = 0) -> PrioritySignal:
    return PrioritySignal(domain=domain, opportunity_value=opportunity_value,
        speed=speed, outcome=outcome, repeatability=repeatability,
        evidence=evidence, freshness=freshness, uncertainty=uncertainty,
        attempts=max(0, attempts), failures=max(0, failures))


def opportunity_signal(domain: str, *, value_jod: float, effort_hours: float,
                       evidence: float = 0.5, freshness_hours: float = 0.0,
                       fit: float = 0.5, risk: float = 0.0) -> PrioritySignal:
    hourly = value_jod / max(0.25, effort_hours)
    value = min(1.0, log1p(max(0.0, hourly)) / log(51.0))
    speed = 1.0 / (1.0 + max(0.0, effort_hours) / 8.0)
    fresh = max(0.0, min(1.0, 1.0 - freshness_hours / 168.0))
    return feedback_from_cycle(
        domain, opportunity_value=value, speed=speed, outcome=max(0.0, min(1.0, fit)),
        repeatability=max(0.0, min(1.0, 1.0 - risk)),
        evidence=max(0.0, min(1.0, evidence)), freshness=fresh,
        uncertainty=1.0 - max(0.0, min(1.0, evidence)))


def learning_update(previous: PrioritySignal, *, outcome: float, success: bool) -> PrioritySignal:
    attempts = previous.attempts + 1
    failures = previous.failures + (0 if success else 1)
    alpha = 0.35
    learned = previous.outcome * (1 - alpha) + max(0.0, min(1.0, outcome)) * alpha
    return feedback_from_cycle(
        previous.domain, opportunity_value=previous.opportunity_value,
        speed=previous.speed, outcome=learned, repeatability=previous.repeatability,
        evidence=min(1.0, previous.evidence + 0.10), freshness=1.0,
        uncertainty=max(0.0, previous.uncertainty * 0.85),
        attempts=attempts, failures=failures)
