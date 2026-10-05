from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class StageState:
    stage: int
    step: int
    status: str
    revision: int


class StageOrchestrator:
    """Durable, gate-driven stage progression for the 41-stage build."""

    KEY = "brain.stage_orchestrator"
    TOTAL_STAGES = 41

    def __init__(self, store: SQLiteStateStore) -> None:
        self.store = store

    def current(self) -> StageState:
        value = self.store.get(self.KEY) or {
            "stage": 1, "step": 1, "status": "PENDING", "revision": 0
        }
        return StageState(**value)

    def advance(self, *, stage: int, step: int, gate_passed: bool) -> StageState:
        if not 1 <= stage <= self.TOTAL_STAGES:
            raise ValueError("stage must be between 1 and 41")
        if step < 1:
            raise ValueError("step must be >= 1")
        if not gate_passed:
            raise RuntimeError("cannot advance without a passing gate")

        def update(current: Any) -> tuple[bool, dict[str, Any]]:
            previous = current or {
                "stage": 1, "step": 1, "status": "PENDING", "revision": 0
            }
            previous_stage = int(previous["stage"])
            if stage < previous_stage:
                raise RuntimeError("stage regression is forbidden")
            revision = int(previous["revision"]) + 1
            status = "COMPLETE" if stage == self.TOTAL_STAGES else "READY"
            return True, {
                "stage": stage,
                "step": step,
                "status": status,
                "revision": revision,
            }

        _, value = self.store.atomic_update(self.KEY, update, default={})
        return StageState(**value)


__all__ = ["StageOrchestrator", "StageState"]
