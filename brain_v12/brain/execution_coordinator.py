"""Unified evidence-first execution coordinator.

Bridges the generic Control Plane, Task Engine, GitHub Agent and bounded
self-healing callbacks without granting any component implicit execution power.
"""
from __future__ import annotations

from typing import Any, Callable

from .control_plane import BrainControlPlane
from .task_engine import TaskEngine

Executor = Callable[[str], dict[str, Any]]
Verifier = Callable[[dict[str, Any]], dict[str, Any] | bool]
Repairer = Callable[[dict[str, Any]], dict[str, Any] | None]


class BrainExecutionCoordinator:
    """Coordinate task state with verified control-plane execution."""

    def __init__(
        self,
        control_plane: BrainControlPlane | None = None,
        task_engine: TaskEngine | None = None,
    ) -> None:
        self.control_plane = control_plane or BrainControlPlane()
        self.task_engine = task_engine or TaskEngine()
        self._links: dict[str, str] = {}

    def create(self, objective: str, max_attempts: int = 3) -> dict[str, Any]:
        control = self.control_plane.create(objective, max_attempts=max_attempts)
        task = self.task_engine.create(objective)
        self._links[control["id"]] = task["id"]
        task["control_task_id"] = control["id"]
        task["max_attempts"] = control["max_attempts"]
        return {"control": control, "task": task}

    def execute(
        self,
        control_task_id: str,
        executor: Executor,
        verifier: Verifier,
        repair: Repairer | None = None,
    ) -> dict[str, Any]:
        task_id = self._links.get(control_task_id)
        if task_id is None:
            return {"ok": False, "error": "TASK_NOT_FOUND"}

        self.task_engine.update(task_id, "RUNNING")
        result = self.control_plane.execute(control_task_id, executor, verifier)
        control = result.get("task", {})
        status = result.get("status", control.get("status"))

        if status == "VERIFIED_COMPLETED":
            evidence = self._evidence_ref(control)
            self.task_engine.complete(task_id, evidence_ref=evidence)
        elif status == "RETRYING":
            self.task_engine.update(task_id, "RETRYING")
            if repair is not None:
                try:
                    repair_result = repair(result)
                except Exception as exc:
                    repair_result = {
                        "ok": False,
                        "error": f"REPAIR_ERROR:{type(exc).__name__}",
                    }
                control.setdefault("evidence", []).append(
                    {"stage": "repair", "result": repair_result}
                )
                result["repair"] = repair_result
        else:
            evidence = self._evidence_ref(control)
            self.task_engine.fail(
                task_id,
                error=result.get("error", control.get("error", "TASK_FAILED")),
                evidence_ref=evidence,
            )

        return {**result, "control": control, "control_task": control, "task": self.task_engine.tasks[task_id]}

    def snapshot(self) -> dict[str, Any]:
        return {
            "control_plane": self.control_plane.snapshot(),
            "task_engine": self.task_engine.snapshot(),
            "links": dict(self._links),
        }

    @staticmethod
    def _evidence_ref(control: dict[str, Any]) -> str | None:
        evidence = control.get("evidence") or []
        if not evidence:
            return None
        verification = next(
            (item for item in reversed(evidence) if item.get("stage") == "verification"),
            None,
        )
        if not verification:
            return None
        result = verification.get("result")
        return result.get("evidence_ref") if isinstance(result, dict) else None
