"""Portable worker/lease protocol for Download-Manager-style APM execution."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
import uuid
from typing import Any


@dataclass
class WorkerLease:
    unit_id: str
    worker_id: str
    lease_id: str
    state: str
    attempt: int
    claimed_at: float
    heartbeat_at: float
    expires_at: float
    result_ref: str | None = None
    evidence_ref: str | None = None

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "WorkerLease":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


class APMWorkerProtocol:
    """Small state machine shared by GitHub, Termux and device workers."""

    def __init__(self, lease_seconds: int = 300):
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.lease_seconds = lease_seconds

    def claim(
        self,
        unit_id: str,
        worker_id: str,
        attempt: int = 1,
        now: float | None = None,
    ) -> WorkerLease:
        t = time.time() if now is None else now
        return WorkerLease(
            unit_id=unit_id,
            worker_id=worker_id,
            lease_id=uuid.uuid4().hex,
            state="CLAIMED",
            attempt=attempt,
            claimed_at=t,
            heartbeat_at=t,
            expires_at=t + self.lease_seconds,
        )

    def heartbeat(
        self,
        lease: WorkerLease,
        now: float | None = None,
    ) -> WorkerLease:
        if lease.state not in {"CLAIMED", "RUNNING"}:
            raise ValueError("heartbeat requires an active lease")
        t = time.time() if now is None else now
        if t > lease.expires_at:
            lease.state = "EXPIRED"
            raise RuntimeError("lease expired")
        lease.state = "RUNNING"
        lease.heartbeat_at = t
        lease.expires_at = t + self.lease_seconds
        return lease

    def complete(
        self,
        lease: WorkerLease,
        result_ref: str,
        evidence_ref: str,
        now: float | None = None,
    ) -> WorkerLease:
        t = time.time() if now is None else now
        if lease.state not in {"CLAIMED", "RUNNING"}:
            raise ValueError("only active leases can complete")
        if t > lease.expires_at:
            lease.state = "EXPIRED"
            raise RuntimeError("lease expired")
        if not result_ref or not evidence_ref:
            raise ValueError("verified completion requires result and evidence")
        lease.state = "VERIFIED_COMPLETED"
        lease.result_ref = result_ref
        lease.evidence_ref = evidence_ref
        lease.heartbeat_at = t
        return lease

    def expire_if_needed(
        self,
        lease: WorkerLease,
        now: float | None = None,
    ) -> WorkerLease:
        t = time.time() if now is None else now
        if lease.state in {"CLAIMED", "RUNNING"} and t > lease.expires_at:
            lease.state = "EXPIRED"
        return lease

    @staticmethod
    def reusable(lease: WorkerLease) -> bool:
        return lease.state == "VERIFIED_COMPLETED" and bool(
            lease.result_ref and lease.evidence_ref
        )

    @staticmethod
    def retryable(lease: WorkerLease) -> bool:
        return lease.state == "EXPIRED"
