"""Bounded dispatcher connecting APM queue and worker leases."""

from __future__ import annotations

from dataclasses import dataclass

from .apm_queue import APMQueue
from .apm_worker_protocol import APMWorkerProtocol, WorkerLease


@dataclass(frozen=True)
class DispatchResult:
    unit_id: str
    worker_id: str
    lease_id: str
    attempt: int


class APMDispatcher:
    def __init__(self, queue: APMQueue, protocol: APMWorkerProtocol | None = None):
        self.queue = queue
        self.protocol = protocol or APMWorkerProtocol()
        self.leases: dict[str, WorkerLease] = {}

    def dispatch(self, worker_id: str) -> DispatchResult | None:
        unit = self.queue.claim(worker_id)
        if unit is None:
            return None
        lease = self.protocol.claim(unit.unit_id, worker_id, unit.attempt)
        self.leases[unit.unit_id] = lease
        return DispatchResult(unit.unit_id, worker_id, lease.lease_id, lease.attempt)

    def heartbeat(self, unit_id: str, now: float | None = None) -> WorkerLease:
        lease = self.leases[unit_id]
        return self.protocol.heartbeat(lease, now)

    def complete(
        self,
        unit_id: str,
        result_ref: str,
        evidence_ref: str,
        now: float | None = None,
    ) -> WorkerLease:
        lease = self.leases[unit_id]
        completed = self.protocol.complete(lease, result_ref, evidence_ref, now)
        self.queue.complete(unit_id)
        return completed

    def recover_expired(self, unit_id: str, now: float | None = None) -> bool:
        lease = self.leases[unit_id]
        self.protocol.expire_if_needed(lease, now)
        if self.protocol.retryable(lease):
            self.queue.mark_expired(unit_id)
            self.queue.requeue_expired(unit_id)
            del self.leases[unit_id]
            return True
        return False

    def pending(self) -> int:
        return len(self.queue.ready())
