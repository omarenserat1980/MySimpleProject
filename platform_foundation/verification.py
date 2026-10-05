from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .audit_chain import AuditChain
from .persistent_state import SQLiteStateStore
from .task_state import TaskStatus


@dataclass(frozen=True)
class VerificationResult:
    task_id: str
    status: TaskStatus
    verified: bool
    output: Any = None
    error: str | None = None


class VerificationGate:
    """Independent post-execution verification gate."""

    def __init__(self, state: SQLiteStateStore, audit: AuditChain) -> None:
        self.state = state
        self.audit = audit

    def verify(
        self,
        task_id: str,
        output: Any,
        verifier: Callable[[Any], bool],
    ) -> VerificationResult:
        if not task_id:
            raise ValueError("task_id is required")

        try:
            verified = bool(verifier(output))
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            verified = False
        else:
            error = None if verified else "verification predicate returned false"

        status = TaskStatus.SUCCESS if verified else TaskStatus.FAILED
        payload = {
            "task_id": task_id,
            "verified": verified,
            "status": status.value,
        }
        if error:
            payload["error"] = error

        self.state.set(
            f"verification:{task_id}",
            {
                "task_id": task_id,
                "status": status.value,
                "verified": verified,
                "error": error,
            },
        )
        self.audit.record("task.verified" if verified else "task.verification_failed", payload)

        return VerificationResult(
            task_id,
            status,
            verified,
            output=output,
            error=error,
        )


__all__ = ["VerificationGate", "VerificationResult"]
