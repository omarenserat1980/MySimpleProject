"""Single-flight execution lock for Brain-owned consequential work.

The lock is intentionally local and file-backed so it can be used by
Termux/Linux Brain runtimes without introducing a paid external service.
It is fail-closed for malformed or actively-held locks and supports bounded
stale-lock recovery using a lease timestamp.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import socket
import time
from uuid import uuid4


class ExecutionLockError(RuntimeError):
    pass


@dataclass(frozen=True)
class LockLease:
    token: str
    task_id: str
    acquired_at: float
    expires_at: float
    host: str
    pid: int

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "task_id": self.task_id,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
            "host": self.host,
            "pid": self.pid,
        }


class BrainExecutionLock:
    """A bounded single-flight lease.

    This is a coordination primitive, not a proof of execution success.
    Success still requires the task's independent verification gate.
    """

    def __init__(self, path: str | Path = ".brain/execution.lock", lease_seconds: int = 3600):
        self.path = Path(path)
        self.lease_seconds = max(1, int(lease_seconds))

    def acquire(self, task_id: str) -> LockLease:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        if self.path.exists():
            existing = self._read()
            if existing and float(existing.get("expires_at", 0)) > now:
                raise ExecutionLockError("EXECUTION_LOCK_HELD")
            # A malformed/expired lease can be recovered, but only because
            # its lease has ended; this is deliberately not unconditional.
            self.path.unlink(missing_ok=True)

        lease = LockLease(
            token=str(uuid4()),
            task_id=str(task_id),
            acquired_at=now,
            expires_at=now + self.lease_seconds,
            host=socket.gethostname(),
            pid=os.getpid(),
        )
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        try:
            fd = os.open(self.path, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(lease.to_dict(), fh, sort_keys=True)
        except FileExistsError as exc:
            raise ExecutionLockError("EXECUTION_LOCK_RACE") from exc
        return lease

    def release(self, lease: LockLease) -> None:
        if not self.path.exists():
            return
        existing = self._read()
        if not existing or existing.get("token") != lease.token:
            raise ExecutionLockError("EXECUTION_LOCK_OWNER_MISMATCH")
        self.path.unlink(missing_ok=True)

    def status(self) -> dict:
        if not self.path.exists():
            return {"locked": False}
        data = self._read()
        if not data:
            return {"locked": True, "state": "MALFORMED"}
        remaining = float(data.get("expires_at", 0)) - time.time()
        return {"locked": remaining > 0, "state": "ACTIVE" if remaining > 0 else "EXPIRED", "lease": data}

    def _read(self) -> dict | None:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None
