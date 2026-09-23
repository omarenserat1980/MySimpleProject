"""Continuous, bounded self-improvement controller for Electronic Brain.

The controller turns measured quality signals into a repeatable improvement
cycle: observe -> choose one safe improvement -> propose -> validate -> test ->
persist -> learn. It never grants shell access, credentials, money movement,
deletion, or arbitrary repository writes.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from time import time
from typing import Any, Iterable, Mapping


@dataclass
class ImprovementCycle:
    cycle_id: int
    objective: str
    trigger: str
    status: str = "PLANNED"
    selected_action: str = ""
    evidence: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time)


class ContinuousSelfImprovement:
    """A persistent decision loop around the bounded coding tool.

    It does not invent a successful modification. If no verified proposal is
    available, the cycle remains PLANNED and records what evidence is needed.
    """

    SAFE_ACTIONS = (
        "improve_tests",
        "improve_reasoning",
        "improve_reliability",
        "improve_observability",
        "improve_documentation",
        "improve_rollback",
    )

    def __init__(self, *, max_history: int = 200) -> None:
        self.max_history = max(10, int(max_history))
        self.history: list[ImprovementCycle] = []
        self.total_cycles = 0

    def choose_action(self, recommendations: Iterable[str], *,
                      quality: float = 0.0,
                      failures: int = 0) -> str:
        recs = [str(x) for x in recommendations]
        if failures > 0 or quality < 0.55:
            return "improve_reliability"
        mapping = {
            "seek_more_evidence": "improve_reasoning",
            "retest_conflicting_hypotheses": "improve_reasoning",
            "generate_more_alternatives": "improve_reasoning",
            "prefer_reversible_plan": "improve_rollback",
        }
        for item in recs:
            if item in mapping:
                return mapping[item]
        return "improve_tests"

    def plan(self, *, objective: str, recommendations: Iterable[str] = (),
             quality: float = 0.0, failures: int = 0,
             evidence: Iterable[str] = ()) -> dict[str, Any]:
        self.total_cycles += 1
        action = self.choose_action(recommendations, quality=quality, failures=failures)
        cycle = ImprovementCycle(
            cycle_id=self.total_cycles,
            objective=str(objective),
            trigger=action,
            selected_action=action,
            evidence=[str(x) for x in evidence if str(x)],
        )
        self.history.append(cycle)
        self.history = self.history[-self.max_history:]
        return asdict(cycle)

    def complete(self, cycle_id: int, *, status: str,
                 result: Mapping[str, Any] | None = None) -> dict[str, Any]:
        for item in reversed(self.history):
            if item.cycle_id == cycle_id:
                item.status = str(status)
                item.result = dict(result or {})
                return asdict(item)
        raise KeyError(f"unknown improvement cycle: {cycle_id}")

    def snapshot(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "continuous_loop": True,
            "cycles": self.total_cycles,
            "history": [asdict(x) for x in self.history[-20:]],
            "safe_actions": list(self.SAFE_ACTIONS),
            "policy": {
                "shell_execution": False,
                "credential_access": False,
                "money_movement": False,
                "arbitrary_deletion": False,
                "external_submission": False,
                "requires_validation_and_regression_tests": True,
                "failed_changes_must_rollback": True,
            },
        }
