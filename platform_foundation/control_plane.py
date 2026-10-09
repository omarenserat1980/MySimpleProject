from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .audit import EvidenceLedger
from .diagnostics import capture_exception
from .permissions import ActionRisk, PermissionBoundary
from .persistent_state import SQLiteStateStore
from .task_state import InvalidTaskTransition, TaskStatus, transition


@dataclass(frozen=True)
class ControlResult:
    task_id: str
    status: TaskStatus
    allowed: bool
    output: Any = None
    error: str | None = None


class ControlPlane:
    """Small auditable execution boundary: permission -> state -> execute -> evidence."""

    def __init__(self, state: SQLiteStateStore, evidence: EvidenceLedger, permissions: PermissionBoundary) -> None:
        self.state = state
        self.evidence = evidence
        self.permissions = permissions
        self._handlers: dict[str, tuple[ActionRisk, Callable[[], Any]]] = {}

    def register(self, task_id: str, action: str, risk: ActionRisk, handler: Callable[[], Any]) -> None:
        if not task_id or not action or not callable(handler):
            raise ValueError("task_id, action and callable handler are required")
        if task_id in self._handlers:
            raise ValueError(f"task already registered: {task_id}")
        self._handlers[task_id] = (risk, handler)
        self.state.set(f"task:{task_id}", {"status": TaskStatus.PENDING.value, "action": action})

    def run(self, task_id: str) -> ControlResult:
        registered = self._handlers.get(task_id)
        if registered is None:
            self.evidence.record("task_missing", {"task_id": task_id})
            return ControlResult(task_id, TaskStatus.FAILED, False, error="task not registered")
        risk, handler = registered
        record = self.state.get(f"task:{task_id}") or {}
        current = TaskStatus(record.get("status", TaskStatus.PENDING.value))
        action = str(record.get("action", ""))
        decision = self.permissions.decide(action, risk)
        if not decision.allowed:
            self.state.set(f"task:{task_id}", {**record, "status": TaskStatus.FAILED.value, "error": decision.reason})
            self.evidence.record("task_denied", {"task_id": task_id, "reason": decision.reason})
            return ControlResult(task_id, TaskStatus.FAILED, False, error=decision.reason)
        try:
            running = transition(current, TaskStatus.RUNNING)
        except InvalidTaskTransition as exc:
            self.evidence.record("task_transition_rejected", {"task_id": task_id, "error": str(exc)})
            return ControlResult(task_id, TaskStatus.FAILED, True, error=str(exc))
        self.state.set(f"task:{task_id}", {**record, "status": running.value})
        try:
            output = handler()
        except Exception as exc:
            diagnostic = capture_exception(task_id, exc)
            self.state.set(f"task:{task_id}", {**record, "status": TaskStatus.FAILED.value, "error": str(exc), "diagnostic": diagnostic.as_dict()})
            self.evidence.record("task_diagnostic", diagnostic.as_dict())
            self.evidence.record("task_failed", {"task_id": task_id, "error": str(exc)})
            return ControlResult(task_id, TaskStatus.FAILED, True, error=str(exc))
        self.state.set(f"task:{task_id}", {**record, "status": TaskStatus.SUCCESS.value})
        self.evidence.record("task_succeeded", {"task_id": task_id})
        return ControlResult(task_id, TaskStatus.SUCCESS, True, output=output)
