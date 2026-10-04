"""Evidence-first Brain Control Plane.

Coordinates task lifecycle without owning unsafe execution. Executors are
explicitly supplied by the caller; completion always requires verification
and an evidence reference.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}

@dataclass
class ControlTask:
    id: str
    objective: str
    status: str = "PENDING"
    attempts: int = 0
    max_attempts: int = 3
    evidence: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

class BrainControlPlane:
    """Bounded execution lifecycle: plan -> execute -> verify -> retry/escalate."""
    def __init__(self) -> None:
        self.tasks: dict[str, ControlTask] = {}

    def create(self, objective: str, max_attempts: int = 3) -> dict[str, Any]:
        task = ControlTask(id=str(uuid4()), objective=objective, max_attempts=max(1, int(max_attempts)))
        self.tasks[task.id] = task
        return self._view(task)

    def attach_verified_evidence(self, task_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None:
            return {"ok": False, "error": "TASK_NOT_FOUND"}
        if not isinstance(evidence, dict) or evidence.get("verified") is not True:
            return {"ok": False, "error": "EVIDENCE_NOT_VERIFIED"}
        evidence_ref = evidence.get("evidence_ref")
        if not evidence_ref:
            return {"ok": False, "error": "EVIDENCE_REFERENCE_REQUIRED"}
        task.evidence.append({"stage": "external_verification", "result": dict(evidence)})
        return {"ok": True, "evidence_ref": evidence_ref, "task": self._view(task)}

    def execute(self, task_id: str, executor: Callable[[str], dict[str, Any]], verifier: Callable[[dict[str, Any]], dict[str, Any] | bool]) -> dict[str, Any]:
        task = self.tasks.get(task_id)
        if task is None: return {"ok": False, "error": "TASK_NOT_FOUND"}
        if task.status in TERMINAL: return {"ok": False, "error": "TASK_NOT_RUNNABLE", "task": self._view(task)}
        if task.attempts >= task.max_attempts:
            task.status = "FAILED"; task.error = "RETRY_LIMIT_REACHED"
            return {"ok": False, "error": task.error, "task": self._view(task)}
        task.status = "RUNNING"; task.attempts += 1
        try:
            result = executor(task.objective)
            if not isinstance(result, dict): raise TypeError("executor must return a mapping")
        except Exception as exc:
            task.status = "FAILED"; task.error = f"EXECUTOR_ERROR:{type(exc).__name__}"
            return {"ok": False, "error": task.error, "task": self._view(task)}
        task.evidence.append({"stage": "execution", "result": result})
        try: verification = verifier(result)
        except Exception as exc: verification = {"verified": False, "reason": f"VERIFIER_ERROR:{type(exc).__name__}"}
        verified = verification is True or (isinstance(verification, dict) and verification.get("verified") is True)
        evidence_ref = verification.get("evidence_ref") if isinstance(verification, dict) else None
        task.evidence.append({"stage": "verification", "result": verification})
        if verified and evidence_ref:
            task.status = "COMPLETED"; task.error = None
            return {"ok": True, "status": "VERIFIED_COMPLETED", "task": self._view(task)}
        task.status = "FAILED"
        task.error = "VERIFICATION_EVIDENCE_REQUIRED" if verified else "VERIFICATION_FAILED"
        if task.attempts < task.max_attempts: task.status = "RETRYING"
        return {"ok": False, "status": task.status, "error": task.error, "task": self._view(task)}

    def snapshot(self) -> dict[str, Any]:
        return {"tasks": [self._view(t) for t in self.tasks.values()], "active": sum(t.status in {"PENDING","RUNNING","RETRYING"} for t in self.tasks.values())}

    @staticmethod
    def _view(task: ControlTask) -> dict[str, Any]:
        return {"id":task.id,"objective":task.objective,"status":task.status,"attempts":task.attempts,"max_attempts":task.max_attempts,"evidence":task.evidence,"error":task.error}
