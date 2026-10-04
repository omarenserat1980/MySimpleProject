"""Autonomous Brain Executive control plane.

The Executive owns internal operational prioritisation. It never bypasses
legal, safety, security, financial-authority, or irreversible-action gates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Iterable


class ActionClass(str, Enum):
    INTERNAL_REVERSIBLE = "INTERNAL_REVERSIBLE"
    EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    IRREVERSIBLE = "IRREVERSIBLE"


@dataclass(frozen=True)
class CompanyObjective:
    objective_id: str
    title: str
    value: float
    urgency: float = 0.0
    evidence: float = 0.0
    cost: float = 1.0
    action_class: ActionClass = ActionClass.INTERNAL_REVERSIBLE
    enabled: bool = True

    @property
    def score(self) -> float:
        return (self.value * 0.55 + self.urgency * 0.20 + self.evidence * 0.25) / max(self.cost, 0.01)

    @property
    def risk_percent(self) -> float:
        """Calculated execution risk, 0-100, from impact, uncertainty and cost exposure."""
        impact = {
            ActionClass.INTERNAL_REVERSIBLE: 10.0,
            ActionClass.EXTERNAL_SIDE_EFFECT: 45.0,
            ActionClass.FINANCIAL: 70.0,
            ActionClass.LEGAL: 60.0,
            ActionClass.IRREVERSIBLE: 85.0,
        }[self.action_class]
        uncertainty = 100.0 - min(max(self.evidence, 0.0), 100.0)
        cost_exposure = 100.0 * max(self.cost, 0.0) / (
            max(self.cost, 0.0) + max(self.value, 0.0) + 1.0
        )
        risk = 0.50 * impact + 0.30 * uncertainty + 0.20 * cost_exposure
        return round(min(max(risk, 0.0), 100.0), 2)

    @property
    def risk_band(self) -> str:
        risk = self.risk_percent
        if risk < 25:
            return "LOW"
        if risk < 50:
            return "MEDIUM"
        if risk < 75:
            return "HIGH"
        return "CRITICAL"


@dataclass(frozen=True)
class ExecutiveDecision:
    objective_id: str
    action: str
    score: float
    status: str
    reason: str
    decision_id: str
    risk_percent: float = 0.0
    risk_band: str = "LOW"


@dataclass
class CompanyState:
    mode: str = "AUTONOMOUS_COMPANY"
    cycle: int = 0
    objectives: list[CompanyObjective] = field(default_factory=list)
    completed: set[str] = field(default_factory=set)
    blocked: set[str] = field(default_factory=set)

    def next_objective(self) -> CompanyObjective | None:
        candidates = [
            x for x in self.objectives
            if x.enabled and x.objective_id not in self.completed
            and x.objective_id not in self.blocked
        ]
        return max(candidates, key=lambda x: (x.score, x.objective_id), default=None)


class BrainExecutive:
    """Deterministic executive loop for autonomous internal company operation."""

    def __init__(self, state: CompanyState | None = None):
        self.state = state or CompanyState()

    @staticmethod
    def _decision_id(objective_id: str, action: str) -> str:
        return sha256(f"{objective_id}|{action}".encode()).hexdigest()[:24]

    @staticmethod
    def _gate(obj: CompanyObjective) -> tuple[bool, str]:
        if obj.action_class is ActionClass.INTERNAL_REVERSIBLE:
            return True, "internal_reversible_action"
        return False, f"authority_gate_required:{obj.action_class.value}"

    def decide(self) -> ExecutiveDecision:
        obj = self.state.next_objective()
        if obj is None:
            return ExecutiveDecision("", "OBSERVE_AND_DISCOVER", 0.0, "NO_OBJECTIVE",
                                     "no eligible objective; discovery required",
                                     self._decision_id("none", "OBSERVE_AND_DISCOVER"),
                                     0.0, "LOW")
        allowed, reason = self._gate(obj)
        action = f"EXECUTE:{obj.objective_id}"
        status = "READY" if allowed else "GATED"
        return ExecutiveDecision(
            obj.objective_id, action, obj.score, status, reason,
            self._decision_id(obj.objective_id, action),
            obj.risk_percent, obj.risk_band,
        )

    def complete(self, objective_id: str) -> None:
        self.state.completed.add(objective_id)
        self.state.cycle += 1

    def block(self, objective_id: str) -> None:
        self.state.blocked.add(objective_id)
        self.state.cycle += 1

    def run_cycle(self) -> ExecutiveDecision:
        decision = self.decide()
        if decision.status == "READY":
            self.complete(decision.objective_id)
        elif decision.status == "GATED" and decision.objective_id:
            self.block(decision.objective_id)
        else:
            self.state.cycle += 1
        return decision

    def load_objectives(self, objectives: Iterable[CompanyObjective]) -> None:
        self.state.objectives.extend(objectives)
