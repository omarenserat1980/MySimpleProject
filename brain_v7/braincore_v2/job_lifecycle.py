"""Bounded job lifecycle engine for internal and external work."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from time import time
from typing import Any


@dataclass
class Job:
    job_id: str
    objective: str
    status: str = "QUEUED"
    owner_id: str = "BRAIN-001"
    attempts: int = 0
    result: dict[str, Any] | None = None
    created_at: float = 0.0
    updated_at: float = 0.0


class JobLifecycle:
    TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}

    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self._counter = 0

    def create(self, objective: str, owner_id: str = "BRAIN-001") -> Job:
        self._counter += 1
        now = time()
        job = Job(f"JOB-{self._counter:06d}", objective, owner_id=owner_id,
                  created_at=now, updated_at=now)
        self.jobs[job.job_id] = job
        return job

    def transition(self, job_id: str, status: str, *, result: dict[str, Any] | None = None) -> Job:
        if status not in {"QUEUED", "RUNNING", "BLOCKED", "COMPLETED", "FAILED", "CANCELLED"}:
            raise ValueError(f"invalid status: {status}")
        job = self.jobs[job_id]
        if job.status in self.TERMINAL and status != job.status:
            raise ValueError("terminal job cannot transition")
        if status == "RUNNING":
            job.attempts += 1
        job.status = status
        job.result = result
        job.updated_at = time()
        return job

    def snapshot(self) -> dict[str, Any]:
        counts = {}
        for job in self.jobs.values():
            counts[job.status] = counts.get(job.status, 0) + 1
        return {"total": len(self.jobs), "by_status": counts,
                "jobs": [asdict(x) for x in self.jobs.values()]}
