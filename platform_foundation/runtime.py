from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .audit import EvidenceLedger
from .failure import FailureTracker
from .health import HealthReport
from .recovery import RecoveryManager
from .security import PermissionPolicy
from .state import StateStore


@dataclass(frozen=True)
class JobResult:
    job_id: str
    status: str
    output: Any = None
    error: str | None = None


class PlatformRuntime:
    """Brain-independent runtime with explicit permission, failure, and recovery boundaries."""

    def __init__(self) -> None:
        self.state = StateStore()
        self.evidence = EvidenceLedger()
        self.permissions = PermissionPolicy()
        self.failures = FailureTracker()
        self.recovery = RecoveryManager(self.state, self.evidence)
        self._jobs: dict[str, tuple[Callable[[], Any], str | None]] = {}
        self._started = False

    def start(self) -> None:
        self._started = True
        self.evidence.record("runtime.start", {"started": True})

    def stop(self) -> None:
        self._started = False
        self.evidence.record("runtime.stop", {"started": False})

    @property
    def started(self) -> bool:
        return self._started

    def register_job(
        self, job_id: str, fn: Callable[[], Any], required_permission: str | None = None
    ) -> None:
        if not job_id or not callable(fn):
            raise ValueError("job_id and callable fn are required")
        if required_permission is not None and not required_permission.strip():
            raise ValueError("required_permission must be non-empty when provided")
        if job_id in self._jobs:
            raise ValueError(f"job already registered: {job_id}")
        self._jobs[job_id] = (fn, required_permission)

    def run_job(self, job_id: str, actor: str = "runtime") -> JobResult:
        if not self._started:
            raise RuntimeError("platform is not started")
        entry = self._jobs.get(job_id)
        if entry is None:
            error = "job not found"
            result = JobResult(job_id, "FAILED", error=error)
            self.failures.record(job_id, LookupError(error))
            self.evidence.record("job.failed", result.__dict__)
            return result
        fn, required_permission = entry
        if required_permission is not None and not self.permissions.is_allowed(required_permission, actor):
            error = f"permission denied for action: {required_permission}"
            result = JobResult(job_id, "DENIED", error=error)
            self.failures.record(job_id, PermissionError(error))
            self.evidence.record("job.denied", {
                "job_id": job_id, "actor": actor, "required_permission": required_permission
            })
            return result
        try:
            output = fn()
            result = JobResult(job_id, "SUCCESS", output=output)
            self.evidence.record("job.success", result.__dict__)
            return result
        except Exception as exc:
            result = JobResult(job_id, "FAILED", error=f"{type(exc).__name__}: {exc}")
            self.failures.record(job_id, exc)
            self.evidence.record("job.failed", result.__dict__)
            return result

    def health(self) -> HealthReport:
        checks = {
            "runtime_started": self._started,
            "state_store": self.state.is_ready(),
            "evidence_ledger": self.evidence.is_ready(),
            "permission_policy": self.permissions.is_ready(),
            "failure_tracker": self.failures.is_ready(),
            "recovery_manager": self.recovery.is_ready(),
        }
        return HealthReport(status="PASS" if self._started else "STOPPED", checks=checks)
