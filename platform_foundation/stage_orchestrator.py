from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class StageState:
    stage: int
    step: int
    status: str
    revision: int
    attempts: int = 0
    last_error: str | None = None


class StageOrchestrator:
    """Durable, gate-driven, sequential progression with resumable execution."""

    KEY = "brain.stage_orchestrator"
    TOTAL_STAGES = 41

    def __init__(self, store: SQLiteStateStore) -> None:
        self.store = store

    def current(self) -> StageState:
        value = self.store.get(self.KEY) or {
            "stage": 1, "step": 1, "status": "READY", "revision": 0,
            "attempts": 0, "last_error": None,
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
                "stage": 1, "step": 1, "status": "READY", "revision": 0,
                "attempts": 0, "last_error": None,
            }
            previous_stage = int(previous["stage"])
            previous_step = int(previous["step"])
            if stage < previous_stage:
                raise RuntimeError("stage regression is forbidden")
            if stage > previous_stage + 1:
                raise RuntimeError("stage skipping is forbidden")
            if stage == previous_stage and step < previous_step:
                raise RuntimeError("step regression is forbidden")
            revision = int(previous["revision"]) + 1
            status = "COMPLETE" if stage == self.TOTAL_STAGES else "READY"
            return True, {
                "stage": stage, "step": step, "status": status,
                "revision": revision, "attempts": 0, "last_error": None,
            }

        _, value = self.store.atomic_update(self.KEY, update, default={})
        return StageState(**value)

    def run_next(
        self,
        *,
        execute: Callable[[StageState], Any],
        verify: Callable[[StageState, Any], bool],
        max_attempts: int = 3,
    ) -> StageState:
        """Execute, persist retry/failure state, verify, then advance durably."""
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        current = self.current()
        attempts = current.attempts
        while attempts < max_attempts:
            attempts += 1
            self.store.set(self.KEY, {
                "stage": current.stage, "step": current.step,
                "status": "RUNNING", "revision": current.revision,
                "attempts": attempts, "last_error": None,
            })
            try:
                result = execute(current)
                if not verify(current, result):
                    raise RuntimeError("stage execution failed independent verification")
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                status = "RETRYING" if attempts < max_attempts else "FAILED"
                self.store.set(self.KEY, {
                    "stage": current.stage, "step": current.step,
                    "status": status, "revision": current.revision,
                    "attempts": attempts, "last_error": error,
                })
                if attempts < max_attempts:
                    continue
                raise RuntimeError(error) from exc

            return self.advance(
                stage=current.stage + 1 if current.stage < self.TOTAL_STAGES else current.stage,
                step=1,
                gate_passed=True,
            )

        raise RuntimeError("stage retry budget exhausted")


__all__ = ["StageOrchestrator", "StageState"]
