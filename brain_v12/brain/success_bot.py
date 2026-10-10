"""Success Bot: goal-to-evidence execution layer for Brain.

Turns a user goal into a bounded execution contract. It measures progress,
requires verification evidence, and never declares success from intent alone.
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict

from .brain_supervisor import BrainSupervisor


@dataclass
class SuccessGoal:
    goal: str
    success_criteria: list[str]
    progress: int = 0
    status: str = "PLANNED"
    evidence: list[dict] | None = None
    goal_id: str | None = None
    job_id: str | None = None

    def __post_init__(self):
        self.evidence = list(self.evidence or [])
        self.goal_id = self.goal_id or "goal-" + uuid.uuid4().hex


class SuccessBot:
    """Deterministic, auditable goal execution facade over BrainSupervisor."""

    def __init__(self, root=None, max_cycles=5):
        if root is None:
            root = os.getenv("BRAIN_SUCCESS_BOT_ROOT")
        if root is None:
            runtime_home = Path(os.getenv("BRAIN_RUNTIME_HOME", "~/.brain/runtime")).expanduser()
            root = runtime_home / "brain6_artifacts" / "success_bot"
        self.supervisor = BrainSupervisor(root=root, max_cycles=max_cycles)
        self.goals: dict[str, SuccessGoal] = {}

    def create_goal(self, goal, success_criteria=None):
        criteria = [str(x).strip() for x in (success_criteria or ["verified_result"]) if str(x).strip()]
        if not goal or not str(goal).strip():
            raise ValueError("goal_required")
        state = SuccessGoal(goal=str(goal).strip(), success_criteria=criteria)
        self.goals[state.goal_id] = state
        state.evidence.append({"ts": time.time(), "event": "goal_created", "goal_id": state.goal_id})
        return state

    def get_goal(self, goal_id):
        return self.goals.get(str(goal_id))

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
        state.job_id = job["job_id"]
        state.evidence.append({"ts": time.time(), "event": "execution_started", "job_id": state.job_id})
        return job

    def verify(self, state, verification):
        verification = dict(verification or {})
        ok = bool(verification.get("verified") or verification.get("ok"))
        return self.update(state, verified=ok, evidence=verification, progress=100 if ok else 90)

    def snapshot(self, state):
        return asdict(state)

    def snapshot_by_id(self, goal_id):
        state = self.get_goal(goal_id)
        if state is None:
            return None
        return self.snapshot(state)
