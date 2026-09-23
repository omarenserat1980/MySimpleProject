"""Inspectable adaptive learning loop for the Electronic Brain.

Learns only from explicit, observable outcomes. Unknown outcomes are retained
as unknown and never converted into success or failure.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from time import time
from typing import Iterable


@dataclass
class StrategyOutcome:
    cycle: int
    objective: str
    strategy: str
    outcome: str  # success, failure, unknown
    reward: float
    evidence: str
    timestamp: float


@dataclass
class StrategyStats:
    strategy: str
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    unknowns: int = 0
    mean_reward: float = 0.0
    weight: float = 0.5


class AdaptiveLearningLoop:
    """Bounded online learning with conservative strategy reweighting."""

    def __init__(self, *, learning_rate: float = 0.20, max_history: int = 500) -> None:
        self.learning_rate = max(0.01, min(1.0, learning_rate))
        self.max_history = max(10, max_history)
        self.history: list[StrategyOutcome] = []
        self.stats: dict[str, StrategyStats] = {}

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, float(value)))

    def _get(self, strategy: str) -> StrategyStats:
        key = strategy.strip() or "UNKNOWN_STRATEGY"
        if key not in self.stats:
            self.stats[key] = StrategyStats(strategy=key)
        return self.stats[key]

    def record_outcome(
        self,
        *,
        cycle: int,
        objective: str,
        strategy: str,
        outcome: str = "unknown",
        reward: float = 0.0,
        evidence: str = "",
    ) -> StrategyStats:
        normalized = outcome.lower().strip()
        if normalized not in {"success", "failure", "unknown"}:
            normalized = "unknown"
        reward = max(-1.0, min(1.0, float(reward)))
        item = StrategyOutcome(
            cycle=cycle,
            objective=objective,
            strategy=strategy,
            outcome=normalized,
            reward=reward,
            evidence=evidence,
            timestamp=time(),
        )
        self.history.append(item)
        self.history = self.history[-self.max_history:]

        stats = self._get(strategy)
        stats.attempts += 1
        if normalized == "success":
            stats.successes += 1
        elif normalized == "failure":
            stats.failures += 1
        else:
            stats.unknowns += 1

        old_reward = stats.mean_reward
        stats.mean_reward = old_reward + self.learning_rate * (reward - old_reward)

        if normalized == "success":
            target = self._clamp(0.5 + 0.5 * reward)
        elif normalized == "failure":
            target = self._clamp(0.25 + 0.25 * reward)
        else:
            target = 0.5 + 0.25 * stats.mean_reward
        stats.weight = self._clamp(
            stats.weight + self.learning_rate * (target - stats.weight)
        )
        return stats

    def recommend(self, candidates: Iterable[str]) -> dict:
        unique = list(dict.fromkeys(c.strip() for c in candidates if c and c.strip()))
        if not unique:
            return {"selected": None, "alternatives": [], "confidence": 0.0}
        scored = []
        for strategy in unique:
            stats = self._get(strategy)
            evidence_count = stats.successes + stats.failures
            calibration = min(1.0, evidence_count / 5.0)
            score = stats.weight * (0.5 + 0.5 * calibration) + 0.5 * stats.mean_reward
            scored.append((strategy, round(score, 4), stats))
        scored.sort(key=lambda x: x[1], reverse=True)
        selected, score, stats = scored[0]
        confidence = self._clamp(
            0.45 + 0.10 * min(stats.attempts, 5) + 0.20 * calibration
            if (calibration := min(1.0, (stats.successes + stats.failures) / 5.0))
            else 0.45
        )
        return {
            "selected": selected,
            "score": round(score, 4),
            "confidence": round(confidence, 4),
            "alternatives": [
                {"strategy": s, "score": sc, "weight": round(st.weight, 4)}
                for s, sc, st in scored[1:]
            ],
        }

    def replan(self, candidates: Iterable[str], *, reason: str = "") -> dict:
        recommendation = self.recommend(candidates)
        recommendation["replan_reason"] = reason
        recommendation["history_size"] = len(self.history)
        return recommendation

    def snapshot(self) -> dict:
        return {
            "learning_rate": self.learning_rate,
            "history_size": len(self.history),
            "strategies": {
                key: asdict(value) for key, value in self.stats.items()
            },
            "recent_outcomes": [asdict(x) for x in self.history[-20:]],
        }
