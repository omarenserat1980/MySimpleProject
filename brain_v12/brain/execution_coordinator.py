"""Unified evidence-first execution coordinator.

Bridges the generic Control Plane, Task Engine, Path Engine and bounded
self-healing callbacks without granting any component implicit execution power.
"""
from __future__ import annotations

from typing import Any, Callable

from .control_plane import BrainControlPlane
from ..path_engine import GateDecision, GateResult, PathEngine, PathRun, PathSpec, PathState
from .task_engine import TaskEngine

Executor = Callable[[str], dict[str, Any]]
Verifier = Callable[[dict[str, Any]], dict[str, Any] | bool]
Repairer = Callable[[dict[str, Any]], dict[str, Any] | None]


class BrainExecutionCoordinator:
    """Single execution owner with PathEngine as the outer bounded path."""

    def __init__(
        self,
        control_plane: BrainControlPlane | None = None,
        task_engine: TaskEngine | None = None,
        path_engine: PathEngine | None = None,
    ) -> None:
        self.control_plane = control_plane or BrainControlPlane()
        self.task_engine = task_engine or TaskEngine()
        self.path_engine = path_engine or PathEngine(
            authorization_gate=self._authorization_gate,
            policy_gate=self._policy_gate,
        )
        self._links: dict[str, str] = {}
        self._path_links: dict[str, str] = {}
        self._path_step_links: dict[str, dict[str, str]] = {}

    @staticmethod
    def _authorization_gate(run: PathRun) -> GateResult:
        if run.spec.require_authorization:
            return GateResult(GateDecision.ALLOW, "execution coordinator authorization")
        return GateResult(GateDecision.ALLOW, "authorization not required")

    @staticmethod
    def _policy_gate(run: PathRun) -> GateResult:
        return GateResult(GateDecision.ALLOW, "coordinator policy")

    def create(self, objective: str, max_attempts: int = 3, steps: list[str] | None = None) -> dict[str, Any]:
        control = self.control_plane.create(objective, max_attempts=max_attempts)
        task = self.task_engine.create(objective)
        path_id = f"execution:{control['id']}"
        path = self.path_engine.start(
            PathSpec(
                path_id=path_id,
                goal=objective,
                steps=steps or ["execute"],
                max_attempts=control["max_attempts"],
                max_steps=len(steps or ["execute"]),
                require_authorization=True,
                metadata={"control_task_id": control["id"]},
            ),
            run_id=path_id,
        )
        self._links[control["id"]] = task["id"]
        self._path_links[control["id"]] = path.run_id
        task["control_task_id"] = control["id"]
        task["path_run_id"] = path.run_id
        task["max_attempts"] = control["max_attempts"]
        return {"control": control, "task": task, "path": self._path_view(path)}

    def create_multistep(self, objective: str, steps: list[str], max_attempts: int = 3) -> dict[str, Any]:
        """Create a path with one non-retrying ControlTask per step.

        PathEngine owns the retry budget; each step ControlTask executes once.
        """
        if not steps:
            raise ValueError("steps are required")
        task = self.task_engine.create(objective)
        path_id = f"path:{task['id']}"
        path = self.path_engine.start(
            PathSpec(
                path_id=path_id,
                goal=objective,
                steps=list(steps),
                max_attempts=max_attempts,
                max_steps=len(steps),
                require_authorization=True,
                metadata={"task_id": task["id"], "multistep": True},
            ),
            run_id=path_id,
        )
        step_links: dict[str, str] = {}
        step_controls: dict[str, Any] = {}
        for step in steps:
            control = self.control_plane.create(f"{step}:{objective}", max_attempts=1)
            step_links[step] = control["id"]
            step_controls[step] = control
        self._path_step_links[path_id] = step_links
        task["path_run_id"] = path_id
        task["max_attempts"] = max_attempts
        return {
            "task": task,
            "path": self._path_view(path),
            "steps": step_controls,
            "step_control_ids": dict(step_links),
        }

    def execute_path_step(
        self,
        path_run_id: str,
        executors: dict[str, Executor],
        verifiers: dict[str, Verifier],
        repairs: dict[str, Repairer] | None = None,
    ) -> dict[str, Any]:
        """Execute only the current path step; PathEngine owns progression."""
        path = self.path_engine.runs.get(path_run_id)
        links = self._path_step_links.get(path_run_id)
        if path is None or links is None:
            return {"ok": False, "error": "PATH_NOT_FOUND"}
        step = path.current_step
        if step is None or step not in links:
            return {"ok": False, "error": "PATH_STEP_NOT_FOUND"}
        executor = executors.get(step)
        verifier = verifiers.get(step)
        if executor is None or verifier is None:
            return {"ok": False, "error": "STEP_HANDLER_NOT_FOUND"}

        control_id = links[step]
        repair = (repairs or {}).get(step)
        self.path_engine.executor = lambda run, current_step: self.control_plane.execute_once(
            links[current_step], executors[current_step], verifiers[current_step]
        )
        self.path_engine.verifier = lambda run, value: (
            isinstance(value, dict) and value.get("status") == "VERIFIED_COMPLETED"
        )
        result = self.path_engine.advance(path_run_id)

        control = self.control_plane.tasks.get(control_id)
        control_view = self.control_plane._view(control) if control is not None else {}
        if result.state == PathState.STOPPED:
            control_view["status"] = "FAILED"
            control_view["error"] = control_view.get("error") or "PATH_ATTEMPT_BUDGET_EXHAUSTED"
        task_id = path.spec.metadata.get("task_id")
        if task_id and result.state == PathState.SUCCEEDED:
            self.task_engine.complete(task_id, evidence_ref=self._evidence_ref(control_view))
        elif task_id and result.state == PathState.STOPPED:
            self.task_engine.fail(task_id, error=control_view.get("error", "PATH_FAILED"))
        return {
            "ok": result.state == PathState.SUCCEEDED,
            "status": "VERIFIED_COMPLETED" if result.state == PathState.SUCCEEDED else result.state.value,
            "step": step,
            "control": control_view,
            "task": self.task_engine.tasks.get(task_id) if task_id else None,
            "path": self._path_view(result),
        }

    def execute(
        self,
        control_task_id: str,
        executor: Executor,
        verifier: Verifier,
        repair: Repairer | None = None,
    ) -> dict[str, Any]:
        task_id = self._links.get(control_task_id)
        path_id = self._path_links.get(control_task_id)
        if task_id is None or path_id is None:
            return {"ok": False, "error": "TASK_NOT_FOUND"}

        self.task_engine.update(task_id, "RUNNING")

        def run_control(_run: PathRun, _step: str) -> dict[str, Any]:
            result = self.control_plane.execute(control_task_id, executor, verifier)
            control = result.get("task", {})
            status = result.get("status", control.get("status"))
            if status == "RETRYING" and repair is not None:
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
            return result

        def verify_path(_run: PathRun, value: Any) -> bool:
            return isinstance(value, dict) and value.get("status") == "VERIFIED_COMPLETED"

        # PathEngine owns the retry budget; one advance invokes the Control
        # Plane exactly once, preventing nested retry loops.
        self.path_engine.executor = run_control
        self.path_engine.verifier = verify_path
        path = self.path_engine.advance(path_id)

        control = self.control_plane.tasks.get(control_task_id)
        control_view = self.control_plane._view(control) if control is not None else {}
        status = control_view.get("status")

        # PathEngine is the authoritative outer budget. If the path has
        # exhausted its attempts, no inner coordinator state may keep it
        # retryable.
        if path.state == PathState.STOPPED:
            status = "FAILED"
            control_view["status"] = "FAILED"
            control_view["error"] = control_view.get("error") or "PATH_ATTEMPT_BUDGET_EXHAUSTED"
            if control is not None:
                control.status = "FAILED"
                control.error = control_view["error"]

        if status == "COMPLETED":
            evidence = self._evidence_ref(control_view)
            self.task_engine.complete(task_id, evidence_ref=evidence)
        elif status == "RETRYING":
            self.task_engine.update(task_id, "RETRYING")
        else:
            evidence = self._evidence_ref(control_view)
            self.task_engine.fail(
                task_id,
                error=control_view.get("error", "TASK_FAILED"),
                evidence_ref=evidence,
            )

        result: dict[str, Any] = {
            "ok": status == "COMPLETED",
            "status": (
                "VERIFIED_COMPLETED"
                if status == "COMPLETED"
                else ("RETRYING" if status == "RETRYING" else control_view.get("status", path.state.value))
            ),
            "control": control_view,
            "control_task": control_view,
            "path": self._path_view(path),
            "task": self.task_engine.tasks[task_id],
        }
        if control_view.get("error"):
            result["error"] = control_view["error"]
        repair_evidence = next(
            (e.get("result") for e in reversed(control_view.get("evidence", [])) if e.get("stage") == "repair"),
            None,
        )
        if repair_evidence is not None:
            result["repair"] = repair_evidence
        return result

    def snapshot(self) -> dict[str, Any]:
        return {
            "control_plane": self.control_plane.snapshot(),
            "task_engine": self.task_engine.snapshot(),
            "path_engine": self._path_snapshot(),
            "links": dict(self._links),
        }

    def _path_snapshot(self) -> dict[str, Any]:
        return {
            "active_by_goal": dict(self.path_engine.active_by_goal),
            "runs": {
                run_id: self._path_view(run)
                for run_id, run in self.path_engine.runs.items()
            },
        }

    @staticmethod
    def _path_view(run: PathRun) -> dict[str, Any]:
        return {
            "run_id": run.run_id,
            "path_id": run.spec.path_id,
            "goal": run.spec.goal,
            "state": run.state.value,
            "step": run.current_step,
            "step_index": run.step_index,
            "attempts": run.attempts,
            "max_attempts": run.spec.max_attempts,
            "last_error": run.last_error,
            "evidence": [
                {
                    "kind": item.kind,
                    "message": item.message,
                    "data": dict(item.data),
                    "timestamp": item.timestamp,
                }
                for item in run.evidence
            ],
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
