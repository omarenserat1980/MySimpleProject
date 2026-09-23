"""Meta-learning controller for Brain V7.

Learns which planning modes perform better from recorded outcomes.
It changes strategy selection, not system permissions. No external side
effects, financial transfers, or unrestricted self-modification are allowed.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt
from typing import Iterable


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass
class StrategyStats:
    mode: str
    attempts: int = 0
    successes: int = 0
    reward_mean: float = 0.5
    last_reward: float = 0.5

    @property
    def success_rate(self) -> float:
        return self.successes / self.attempts if self.attempts else 0.0

    @property
    def confidence(self) -> float:
        return min(1.0, sqrt(self.attempts) / 5.0)

    @property
    def uncertainty(self) -> float:
        return 1.0 - self.confidence


@dataclass(frozen=True)
class StrategyObservation:
    mode: str
    reward: float
    success: bool
    context: str = ""


def update(stats: StrategyStats, observation: StrategyObservation) -> StrategyStats:
    reward = _clamp(observation.reward)
    stats.attempts += 1
    stats.successes += int(observation.success)
    learning_rate = 1.0 / stats.attempts
    stats.reward_mean += learning_rate * (reward - stats.reward_mean)
    stats.last_reward = reward
    return stats


def learn(
    history: Iterable[StrategyObservation],
    modes: Iterable[str] = ("EXPLOIT", "IMPROVE", "EXPLORE", "COMPOSE"),
) -> dict[str, StrategyStats]:
    table = {m: StrategyStats(mode=m) for m in modes}
    for obs in history:
        if obs.mode in table:
            update(table[obs.mode], obs)
    return table


def strategy_value(stats: StrategyStats, exploration: float = 0.20) -> float:
    # Bounded UCB-style exploration: unfamiliar strategies receive a
    # controlled bonus without overwhelming demonstrated performance.
    bonus = exploration * stats.uncertainty
    return _clamp(stats.reward_mean * 0.70 + stats.success_rate * 0.20 + bonus * 0.10)


def choose_strategy(
    stats: Iterable[StrategyStats],
    *,
    minimum_exploration: float = 0.10,
) -> dict:
    rows = []
    for item in stats:
        value = strategy_value(item, exploration=max(0.0, minimum_exploration))
        rows.append({
            "mode": item.mode,
            "value": round(value, 4),
            "attempts": item.attempts,
            "success_rate": round(item.success_rate, 4),
            "reward_mean": round(item.reward_mean, 4),
            "uncertainty": round(item.uncertainty, 4),
        })
    rows.sort(key=lambda x: x["value"], reverse=True)
    selected = rows[0] if rows else None
    return {
        "selected": selected,
        "ranked_strategies": rows,
        "reason": "meta_learned_strategy_value" if selected else "no_strategy_data",
        "external_side_effects": False,
        "permission_escalation": False,
    }


def recommend(
    history: Iterable[StrategyObservation],
    *,
    exploration_budget: float = 0.20,
) -> dict:
    stats = learn(history)
    decision = choose_strategy(stats, minimum_exploration=exploration_budget)
    return {
        "decision": decision,
        "memory": [asdict(s) for s in stats.values()],
        "learning_rule": "reward_and_success_with_bounded_exploration",
    }


def stability_guard(
    previous_mode: str | None,
    selected_mode: str | None,
    *,
    switch_margin: float = 0.08,
    previous_value: float = 0.0,
    selected_value: float = 0.0,
) -> dict:
    """Prevent rapid strategy oscillation when alternatives are nearly equal."""
    if not previous_mode or not selected_mode or previous_mode == selected_mode:
        return {"mode": selected_mode, "switched": previous_mode != selected_mode}
    if selected_value - previous_value < max(0.0, switch_margin):
        return {
            "mode": previous_mode,
            "switched": False,
            "reason": "hysteresis_prevents_oscillation",
        }
    return {
        "mode": selected_mode,
        "switched": True,
        "reason": "meaningful_strategy_improvement",
    }
