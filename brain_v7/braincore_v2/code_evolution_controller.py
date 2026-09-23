"""Control plane for the Brain's self-improvement coding lifecycle.

The controller turns a proposed source change into an auditable lifecycle:
QUEUED -> VALIDATED -> CHECKPOINTED -> APPLIED -> TESTED -> PERSISTED.
A failed regression moves the change to ROLLED_BACK. External persistence is
never assumed; GitHub persistence is reported only by the executor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any, Iterable

from .code_workspace_tool import CodeChange
from .code_tool_engineering_team import CodeToolEngineeringTeam


@dataclass
class CodeEvolutionJob:
    job_id: str
    objective: str
    commit_message: str
    status: str = "QUEUED"
    created_at: float = field(default_factory=time)
    updated_at: float = field(default_factory=time)
    result: dict[str, Any] = field(default_factory=dict)


class CodeEvolutionController:
    """Bounded coordinator for repeated safe code-improvement cycles."""

    def __init__(self, team: CodeToolEngineeringTeam, *, max_history: int = 200) -> None:
        self.team = team
        self.max_history = max(20, max_history)
        self.jobs: list[CodeEvolutionJob] = []

    def enqueue(self, objective: str, *, commit_message: str = "brain: safe self-improvement") -> CodeEvolutionJob:
        job = CodeEvolutionJob(
            job_id=f"CODE-JOB-{len(self.jobs)+1:06d}",
            objective=str(objective).strip(),
            commit_message=str(commit_message).strip() or "brain: safe self-improvement",
        )
        self.jobs.append(job)
        self.jobs = self.jobs[-self.max_history:]
        return job

    def execute(
        self,
        changes: Iterable[CodeChange],
        *,
        objective: str,
        commit_message: str = "brain: safe self-improvement",
        persist_to_github: bool = True,
    ) -> dict[str, Any]:
        job = self.enqueue(objective, commit_message=commit_message)
        job.status = "VALIDATING"
        job.updated_at = time()
        try:
            result = self.team.execute_autonomous_change(
                list(changes),
                reason=objective,
                commit_message=job.commit_message,
                remote=persist_to_github,
            )
        except Exception as exc:
            job.status = "FAILED"
            job.result = {"error": str(exc)}
            job.updated_at = time()
            return {"job": asdict(job), "status": "FAILED", "error": str(exc)}

        job.result = result
        remote_status = result.get("remote_status")
        if result.get("status") == "ROLLED_BACK":
            job.status = "ROLLED_BACK"
        elif result.get("status") == "APPLIED_LOCALLY" and remote_status == "COMMITTED":
            job.status = "PERSISTED"
        elif result.get("status") == "APPLIED_LOCALLY":
            job.status = "TESTED"
        else:
            job.status = str(result.get("status", "COMPLETED"))
        job.updated_at = time()
        return {"job": asdict(job), "status": job.status, "result": result}

    def snapshot(self) -> dict[str, Any]:
        return {
            "jobs": [asdict(x) for x in self.jobs[-50:]],
            "job_count": len(self.jobs),
            "team": self.team.capability_status(),
            "safe_lifecycle": [
                "QUEUED", "VALIDATING", "CHECKPOINTED", "APPLIED",
                "TESTED", "PERSISTED", "ROLLED_BACK", "FAILED",
            ],
        }
