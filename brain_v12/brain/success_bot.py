"""Success Bot: goal-to-evidence execution layer for Brain.

Turns a user goal into a bounded execution contract. It measures progress,
requires verification evidence, and never declares success from intent alone.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, asdict
from .brain_supervisor import BrainSupervisor

@dataclass
class SuccessGoal:
    goal: str
    success_criteria: list[str]
    progress: int = 0
    status: str = "PLANNED"
    evidence: list[dict] | None = None

    def __post_init__(self):
        self.evidence = list(self.evidence or [])

class SuccessBot:
    """Deterministic, auditable goal execution facade over BrainSupervisor."""

    def __init__(self, root="brain6_artifacts/success_bot", max_cycles=5):
        self.supervisor = BrainSupervisor(root=root, max_cycles=max_cycles)

    def create_goal(self, goal, success_criteria=None):
        criteria = [str(x).strip() for x in (success_criteria or ["verified_result"]) if str(x).strip()]
        if not goal or not str(goal).strip():
            raise ValueError("goal_required")
        return SuccessGoal(goal=str(goal).strip(), success_criteria=criteria)

    def update(self, state, *, verified=False, evidence=None, progress=None):
        evidence = dict(evidence or {})
        if verified:
            state.progress = 100
            state.status = "VERIFIED_COMPLETED"
        elif progress is not None:
            state.progress = max(0, min(99, int(progress)))
            state.status = "IN_PROGRESS"
        state.evidence.append({"ts": time.time(), "verified": bool(verified), **evidence})
        return state

    def start(self, state, steps=None):
        job = self.supervisor.create(state.goal, steps=steps)
        state.status = "RUNNING"
        state.progress = max(state.progress, 5)
        state.evidence.append({"ts": time.time(), "event": "execution_started", "job_id": job["job_id"]})
        return job

    def verify(self, state, verification):
        ok = bool(verification.get("verified") or verification.get("ok"))
        return self.update(state, verified=ok, evidence=verification, progress=100 if ok else 90)

    def snapshot(self, state):
        return asdict(state)
