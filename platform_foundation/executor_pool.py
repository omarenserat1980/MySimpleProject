from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable
import uuid

from .audit_chain import AuditChain
from .execution_policy import BrainExecutionPolicy, ExecutorDecision, ExecutorDescriptor
from .lease import TaskLease
from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class ExecutorJob:
    job_id: str
    task: str
    status: str = "PENDING"
    attempts: int = 0
    executor_id: str | None = None
    output: Any = None
    error: str | None = None


class BrainExecutorPool:
    """Provider-independent durable executor pool owned by Brain.

    The pool selects an executor by BrainExecutionPolicy, claims a durable
    lease before execution, fences the final commit, and leaves RUNNING state
    recoverable after a process/device crash. Windows/GitHub/Android are
    merely possible executors; none is a control-plane dependency.
    """

    def __init__(
        self,
        store: SQLiteStateStore,
        audit: AuditChain,
        executors: list[ExecutorDescriptor],
        *,
        policy: BrainExecutionPolicy | None = None,
        lease: TaskLease | None = None,
    ) -> None:
        self.store = store
        self.audit = audit
        self.executors = list(executors)
        self.policy = policy or BrainExecutionPolicy()
        self.lease = lease or TaskLease(store, audit)
        self.handlers: dict[str, Callable[[ExecutorJob], Any]] = {}
        self.verifiers: dict[str, Callable[[ExecutorJob, Any], bool]] = {}

    @staticmethod
    def _key(job_id: str) -> str:
        return f"executor.job:{job_id}"

    def register(
        self,
        task: str,
        handler: Callable[[ExecutorJob], Any],
        verifier: Callable[[ExecutorJob, Any], bool],
    ) -> None:
        if not task or not callable(handler) or not callable(verifier):
            raise ValueError("task, handler and verifier are required")
        self.handlers[task] = handler
        self.verifiers[task] = verifier

    def submit(self, job_id: str, task: str) -> ExecutorJob:
        if not job_id or not task:
            raise ValueError("job_id and task are required")
        if task not in self.handlers:
            raise ValueError(f"task_not_registered:{task}")
        if self.store.get(self._key(job_id)) is not None:
            raise ValueError(f"job_already_exists:{job_id}")
        job = ExecutorJob(job_id=job_id, task=task)
        self.store.set(self._key(job_id), asdict(job))
        self.audit.record("executor.job.submitted", {"job_id": job_id, "task": task})
        return job

    def current(self, job_id: str) -> ExecutorJob | None:
        value = self.store.get(self._key(job_id))
        if value is None:
            return None
        return ExecutorJob(**value)

    def readiness(self, required_capabilities: set[str] | None = None) -> dict[str, Any]:
        decision = self.policy.select(
            self.executors,
            required_capabilities=required_capabilities,
        )
        return {
            "ready": decision.decision is ExecutorDecision.ALLOWED,
            "decision": decision.decision.value,
            "executor_id": decision.executor_id,
            "reason": decision.reason,
            "executors": [
                {
                    "executor_id": item.executor_id,
                    "owner": item.owner,
                    "persistent": item.persistent,
                    "capabilities": sorted(item.capabilities),
                }
                for item in self.executors
            ],
        }

    def dispatch(
        self,
        job_id: str,
        *,
        required_capabilities: set[str] | None = None,
        lease_ttl_seconds: float = 60.0,
        owner_id: str | None = None,
    ) -> ExecutorJob:
        job = self.current(job_id)
        if job is None:
            raise ValueError(f"unknown_job:{job_id}")
        if job.status == "SUCCESS":
            return job
        if lease_ttl_seconds <= 0:
            raise ValueError("lease_ttl_seconds must be positive")

        decision = self.policy.select(
            self.executors,
            required_capabilities=required_capabilities,
        )
        if decision.decision is not ExecutorDecision.ALLOWED:
            blocked = ExecutorJob(
                **{**asdict(job), "status": "BLOCKED", "error": decision.reason}
            )
            self.store.set(self._key(job_id), asdict(blocked))
            self.audit.record(
                "executor.job.blocked",
                {"job_id": job_id, "reason": decision.reason},
            )
            return blocked

        executor_id = decision.executor_id
        owner = owner_id or f"executor:{executor_id}:{uuid.uuid4().hex}"
        lease_result = self.lease.acquire(
            job_id, owner, ttl_seconds=lease_ttl_seconds
        )
        if not lease_result.acquired:
            self.audit.record(
                "executor.job.lease_denied",
                {"job_id": job_id, "executor_id": executor_id},
            )
            return self.current(job_id) or job

        running = ExecutorJob(
            **{
                **asdict(job),
                "status": "RUNNING",
                "attempts": job.attempts + 1,
                "executor_id": executor_id,
                "error": None,
            }
        )
        self.store.set(self._key(job_id), asdict(running))
        self.audit.record(
            "executor.job.started",
            {"job_id": job_id, "executor_id": executor_id, "attempt": running.attempts},
        )

        try:
            handler = self.handlers[running.task]
            verifier = self.verifiers[running.task]
            output = handler(running)
            if not verifier(running, output):
                raise RuntimeError("independent verification failed")
            if not self.lease.is_owned(job_id, owner):
                raise RuntimeError("execution lease lost before commit")
            completed = ExecutorJob(
                **{**asdict(running), "status": "SUCCESS", "output": output}
            )
            self.store.set(self._key(job_id), asdict(completed))
            self.audit.record(
                "executor.job.verified",
                {"job_id": job_id, "executor_id": executor_id},
            )
            return completed
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            if self.lease.is_owned(job_id, owner):
                failed = ExecutorJob(
                    **{**asdict(running), "status": "FAILED", "error": error}
                )
                self.store.set(self._key(job_id), asdict(failed))
                result = failed
            else:
                result = self.current(job_id) or running
            self.audit.record(
                "executor.job.failed",
                {"job_id": job_id, "executor_id": executor_id, "error": error},
            )
            return result
        finally:
            self.lease.release(job_id, owner)


__all__ = ["BrainExecutorPool", "ExecutorJob"]
