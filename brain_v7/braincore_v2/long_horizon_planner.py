"""Bounded long-horizon planner with simulation and replanning."""
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class PlanStep:
    action: str
    expected: Any = None
    cost: float = 1.0
    risk: float = 0.0

@dataclass
class Plan:
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    score: float = 0.0

class LongHorizonPlanner:
    def __init__(self):
        self.simulators: dict[str, Callable[[dict], Any]] = {}
        self.history: list[Plan] = []

    def register_simulator(self, action: str, simulator: Callable[[dict], Any]):
        self.simulators[action] = simulator

    def propose(self, goal: str, actions: list[str], horizon: int = 5) -> Plan:
        steps = [PlanStep(action=a) for a in actions[:max(1, horizon)]]
        return Plan(goal=goal, steps=steps)

    def simulate(self, plan: Plan, state: dict) -> Plan:
        current = dict(state)
        total = 0.0
        for step in plan.steps:
            sim = self.simulators.get(step.action)
            if sim is None:
                step.risk = 1.0
                total -= 1.0
                continue
            try:
                predicted = sim(current)
                step.expected = predicted
                current["predicted"] = predicted
                total += 1.0
            except Exception:
                step.risk = 1.0
                total -= 2.0
            total -= step.cost * 0.1
            total -= step.risk
        plan.score = total
        self.history.append(plan)
        return plan

    def replan(self, plan: Plan, failed_action: str, alternatives: list[str]) -> Plan:
        remaining = [s.action for s in plan.steps if s.action != failed_action]
        remaining = alternatives[:1] + remaining
        return self.propose(plan.goal, remaining, len(remaining))

    def status(self):
        return {"plans": len(self.history), "simulators": sorted(self.simulators)}
