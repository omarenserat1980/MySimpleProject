"""Mission state machine for Brain V13.

A mission is a durable objective; tasks are implementation details underneath it.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
import time
from typing import Any


class MissionState(str, Enum):
    CREATED = "CREATED"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    DIAGNOSING = "DIAGNOSING"
    RECOVERING = "RECOVERING"
    RETEST = "RETEST"
    ESCALATED = "ESCALATED"


_ALLOWED = {
    MissionState.CREATED: {MissionState.UNDERSTANDING, MissionState.ESCALATED},
    MissionState.UNDERSTANDING: {MissionState.PLANNING, MissionState.ESCALATED},
    MissionState.PLANNING: {MissionState.READY, MissionState.ESCALATED},
    MissionState.READY: {MissionState.EXECUTING, MissionState.ESCALATED},
    MissionState.EXECUTING: {MissionState.OBSERVING, MissionState.DIAGNOSING},
    MissionState.OBSERVING: {MissionState.VERIFYING, MissionState.DIAGNOSING},
    MissionState.VERIFYING: {MissionState.COMPLETED, MissionState.DIAGNOSING, MissionState.ESCALATED},
    MissionState.DIAGNOSING: {MissionState.RECOVERING, MissionState.ESCALATED},
    MissionState.RECOVERING: {MissionState.RETEST, MissionState.ESCALATED},
    MissionState.RETEST: {MissionState.VERIFYING, MissionState.DIAGNOSING, MissionState.ESCALATED},
    MissionState.COMPLETED: set(),
    MissionState.ESCALATED: set(),
}


@dataclass
class Mission:
    mission_id: str
    objective: str
    success_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    state: MissionState = MissionState.CREATED
    attempts: int = 0
    max_attempts: int = 3
    evidence_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def transition(self, target: MissionState, *, reason: str = "") -> "Mission":
        if target not in _ALLOWED[self.state]:
            raise ValueError(f"invalid_mission_transition:{self.state}->{target}")
        if target in {MissionState.EXECUTING, MissionState.RETEST}:
            if self.attempts >= self.max_attempts:
                raise ValueError("mission_attempt_limit_reached")
            self.attempts += 1
        self.state = target
        self.updated_at = time.time()
        if reason:
            self.metadata.setdefault("transition_reasons", []).append(
                {"from": self.state.value, "to": target.value, "reason": reason, "ts": self.updated_at}
            )
        return self

    def can_retry(self) -> bool:
        return self.attempts < self.max_attempts

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data
