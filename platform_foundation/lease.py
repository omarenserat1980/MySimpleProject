from __future__ import annotations

import time
from dataclasses import dataclass

from .audit_chain import AuditChain
from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class LeaseResult:
    task_id: str
    owner: str
    acquired: bool
    expires_at: float | None = None
    reason: str | None = None


class TaskLease:
    """Durable single-owner lease with expiry and audit evidence."""

    def __init__(self, state: SQLiteStateStore, audit: AuditChain) -> None:
        self.state = state
        self.audit = audit

    def acquire(self, task_id: str, owner: str, ttl_seconds: float = 60.0) -> LeaseResult:
        if not task_id or not owner:
            raise ValueError("task_id and owner are required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = time.time()
        expires_at = now + ttl_seconds
        key = f"lease:{task_id}"

        def claim(current):
            if current and float(current["expires_at"]) > now and current["owner"] != owner:
                return False, current
            return True, {"owner": owner, "expires_at": expires_at}

        acquired, current = self.state.atomic_update(key, claim)
        if not acquired:
            self.audit.record("lease.denied", {
                "task_id": task_id, "owner": owner, "reason": "owned",
            })
            return LeaseResult(task_id, owner, False, reason="lease owned")
        self.audit.record("lease.acquired", {
            "task_id": task_id, "owner": owner, "expires_at": expires_at,
        })
        return LeaseResult(task_id, owner, True, expires_at=expires_at)

    def heartbeat(self, task_id: str, owner: str, ttl_seconds: float = 60.0) -> LeaseResult:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = time.time()
        expires_at = now + ttl_seconds

        def renew(current):
            if not current or current["owner"] != owner or float(current["expires_at"]) <= now:
                return False, current
            return True, {"owner": owner, "expires_at": expires_at}

        renewed, current = self.state.atomic_update(f"lease:{task_id}", renew)
        if not renewed:
            self.audit.record("lease.heartbeat_denied", {"task_id": task_id, "owner": owner})
            return LeaseResult(task_id, owner, False, reason="lease not owned")
        self.audit.record("lease.heartbeat", {
            "task_id": task_id, "owner": owner, "expires_at": expires_at,
        })
        return LeaseResult(task_id, owner, True, expires_at=expires_at)

    def release(self, task_id: str, owner: str) -> bool:
        def release_if_owned(current):
            if not current or current["owner"] != owner:
                return False, current
            return True, {"owner": None, "expires_at": 0.0}

        released, _ = self.state.atomic_update(f"lease:{task_id}", release_if_owned)
        if not released:
            self.audit.record("lease.release_denied", {"task_id": task_id, "owner": owner})
            return False
        self.audit.record("lease.released", {"task_id": task_id, "owner": owner})
        return True
