from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .audit import EvidenceLedger
from .health import HealthReport
from .state import StateStore


@dataclass(frozen=True)
class JobResult:
    job_id: str
    status: str
    output: Any = None
    error: str | None = None


class PlatformRuntime:
    """Brain-independent minimal runtime for the Base Expansion foundation."""

    def __init__(self) -> None:
        self.state = StateStore()
        self.evidence = EvidenceLedger()
        self._jobs: dict[str, Callable[[], Any]] = {}
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

    def register_job(self, job_id: str, fn: Callable[[], Any]) -> None:
        if not job_id or not callable(fn):
            raise ValueError("job_id and callable fn are required")
        if job_id in self._jobs:
            raise ValueError(f"job already registered: {job_id}")
        self._jobs[job_id] = fn

    def run_job(self, job_id: str) -> JobResult:
        if not self._started:
            raise RuntimeError("platform is not started")
        fn = self._jobs.get(job_id)
        if fn is None:
            result = JobResult(job_id, "FAILED", error="job not found")
            self.evidence.record("job.failed", result.__dict__)
            return result
        try:
            output = fn()
            result = JobResult(job_id, "SUCCESS", output=output)
            self.evidence.record("job.success", result.__dict__)
            return result
        except Exception as exc:
            result = JobResult(job_id, "FAILED", error=f"{type(exc).__name__}: {exc}")
            self.evidence.record("job.failed", result.__dict__)
            return result

    def health(self) -> HealthReport:
        return HealthReport(
            status="PASS" if self._started else "STOPPED",
            checks={
                "runtime_started": self._started,
                "state_store": self.state.is_ready(),
                "evidence_ledger": self.evidence.is_ready(),
            },
        )
