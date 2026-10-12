"""Brain Execution Fabric.

A single capability-oriented execution layer over local and remote Brain-owned
workers. GitHub is never an execution fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
import uuid
from typing import Any, Callable

from .execution_gateway import BrainExecutionGateway
from .internal_task_runtime import InternalTaskRuntime


@dataclass
class Worker:
    worker_id: str
    capabilities: set[str]
    kind: str
    executor: Callable[[list[str], str, int | None], dict[str, Any]]
    online: bool = True
    external: bool = False
    last_seen: float = field(default_factory=time.time)


class ExecutionFabric:
    def __init__(self, runtime: InternalTaskRuntime | None = None):
        self.runtime = runtime or InternalTaskRuntime()
        self.workers: dict[str, Worker] = {}
        self.leases: dict[str, dict[str, Any]] = {}

    def register(self, worker_id: str, kind: str, capabilities: set[str],
                 executor: Callable[[list[str], str, int | None], dict[str, Any]],
                 *, external: bool = False) -> None:
        if external:
            raise RuntimeError("EXTERNAL_WORKER_FORBIDDEN")
        self.workers[worker_id] = Worker(
            worker_id=worker_id, kind=kind, capabilities=set(capabilities),
            executor=executor,
        )

    def heartbeat(self, worker_id: str, *, online: bool = True) -> None:
        worker = self.workers[worker_id]
        worker.online = online
        worker.last_seen = time.time()

    def resolve(self, capability: str) -> Worker:
        candidates = [
            w for w in self.workers.values()
            if w.online and not w.external and capability in w.capabilities
        ]
        if not candidates:
            raise RuntimeError(f"NO_BRAIN_WORKER_FOR:{capability}")
        return sorted(candidates, key=lambda w: (w.kind != "local", w.worker_id))[0]

    def submit(self, task: str, argv: list[str], capability: str = "brain-internal-execution",
               metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        worker = self.resolve(capability)
        item = self.runtime.enqueue(
            task, argv, capability,
            {**(metadata or {}), "worker_id": worker.worker_id, "worker_kind": worker.kind},
        )
        return {**item, "worker_id": worker.worker_id, "worker_kind": worker.kind}

    def execute(self, task_id: str, argv: list[str], capability: str,
                timeout: int | None = None) -> dict[str, Any]:
        """Reject the legacy direct-worker execution path.

        Consequential execution must enter through InternalTaskRuntime so the
        canonical gateway, execution contract, idempotency, leadership/fencing
        checks, and evidence path remain in control. Direct worker invocation
        is intentionally fail-closed rather than treated as trusted execution.
        """
        raise RuntimeError(
            "DIRECT_WORKER_EXECUTION_FORBIDDEN_USE_INTERNAL_TASK_RUNTIME"
        )

    def recover(self) -> dict[str, Any]:
        active = [
            lease for lease in self.leases.values()
            if lease.get("state") == "RUNNING"
        ]
        return {"active_leases": active, "durable_pending": self.runtime.pending()}

    def status(self) -> dict[str, Any]:
        return {
            "fabric": "brain-execution-fabric",
            "github_execution_dependency": False,
            "workers": [
                {
                    "worker_id": w.worker_id, "kind": w.kind,
                    "capabilities": sorted(w.capabilities),
                    "online": w.online,
                    "external": w.external,
                    "last_seen": w.last_seen,
                }
                for w in self.workers.values()
            ],
            "leases": list(self.leases.values()),
            "runtime": self.runtime.status(),
        }
