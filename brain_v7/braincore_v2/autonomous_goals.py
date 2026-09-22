"""Autonomous goal generation and bounded planning."""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class GoalCandidate:
    id: str
    description: str
    priority: float
    reason: str
    steps: list[str] = field(default_factory=list)

class AutonomousGoalEngine:
    def __init__(self):
        self.candidates: list[GoalCandidate] = []
        self.completed: set[str] = set()

    def generate(self, state: dict[str, Any]) -> list[GoalCandidate]:
        gaps = state.get("gaps", [])
        objective = state.get("objective", "improve current state")
        result = []
        for i, gap in enumerate(gaps):
            gid = f"auto-{len(self.candidates)+i+1}"
            result.append(GoalCandidate(
                id=gid,
                description=f"{objective}: {gap}",
                priority=max(0.1, 1.0 - i * 0.1),
                reason="identified_gap",
                steps=["inspect", "plan", "act", "observe", "evaluate"],
            ))
        if not result:
            result.append(GoalCandidate(
                id=f"auto-{len(self.candidates)+1}",
                description=f"{objective}: inspect current state",
                priority=0.5,
                reason="no_explicit_gap",
                steps=["inspect", "observe", "evaluate"],
            ))
        self.candidates.extend(result)
        return result

    def select(self) -> GoalCandidate | None:
        pending = [g for g in self.candidates if g.id not in self.completed]
        return max(pending, key=lambda g: g.priority, default=None)

    def complete(self, goal_id: str):
        self.completed.add(goal_id)

    def status(self):
        return {
            "candidates": len(self.candidates),
            "completed": len(self.completed),
            "pending": len([g for g in self.candidates if g.id not in self.completed]),
        }
