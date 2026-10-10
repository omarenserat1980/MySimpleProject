from __future__ import annotations

"""Single admission authority for Brain execution.

This is deliberately small and stdlib-only. It does not execute work; it decides
whether work is allowed to enter the execution plane. The invariant is:
one intent fingerprint -> one active lease, and capacity must be explicitly admitted.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import os
import time
from typing import Any


@dataclass(frozen=True)
class ExecutionLease:
    lease_id: str
    fingerprint: str
    intent_id: str
    owner: str
    acquired_at: float
    expires_at: float
    status: str = "ACTIVE"


class ExecutionAuthority:
    def __init__(self, state_path: str | Path = ".brain/state/execution_authority.json",
                 lease_seconds: int = 900, max_active: int = 1) -> None:
        self.path = Path(state_path)
        self.lease_seconds = max(30, int(lease_seconds))
        self.max_active = max(1, int(max_active))

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"leases": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"leases": {}}

    def _save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def fingerprint(intent_id: str, operation: str, payload: dict[str, Any] | None = None) -> str:
        body = json.dumps({
            "intent_id": intent_id,
            "operation": operation,
            "payload": payload or {},
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def reap(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        state = self._load()
        leases = state.get("leases", {})
        expired = [k for k, v in leases.items() if v.get("status") == "ACTIVE"
                   and float(v.get("expires_at", 0)) <= now]
        for k in expired:
            leases[k]["status"] = "EXPIRED"
        if expired:
            self._save(state)
        return len(expired)

    def acquire(self, *, intent_id: str, operation: str, owner: str,
                payload: dict[str, Any] | None = None,
                capacity_admitted: bool = True) -> dict[str, Any]:
        if not capacity_admitted:
            return {"ok": False, "status": "CAPACITY_BLOCKED"}

        self.reap()
        state = self._load()
        leases = state.setdefault("leases", {})
        fp = self.fingerprint(intent_id, operation, payload)

        for lease in leases.values():
            if lease.get("fingerprint") == fp and lease.get("status") == "ACTIVE":
                return {"ok": True, "status": "IDEMPOTENT_REUSE", "lease": lease}

        active = [x for x in leases.values() if x.get("status") == "ACTIVE"]
        if len(active) >= self.max_active:
            return {"ok": False, "status": "EXECUTION_BUSY",
                    "active_count": len(active), "max_active": self.max_active}

        now = time.time()
        lease = ExecutionLease(
            lease_id=hashlib.sha256(f"{fp}:{now}".encode()).hexdigest()[:24],
            fingerprint=fp,
            intent_id=intent_id,
            owner=owner,
            acquired_at=now,
            expires_at=now + self.lease_seconds,
        )
        leases[lease.lease_id] = asdict(lease)
        self._save(state)
        return {"ok": True, "status": "ADMITTED", "lease": asdict(lease)}

    def release(self, lease_id: str, final_status: str = "RELEASED") -> dict[str, Any]:
        state = self._load()
        lease = state.setdefault("leases", {}).get(lease_id)
        if not lease:
            return {"ok": False, "status": "LEASE_NOT_FOUND"}
        lease["status"] = final_status
        self._save(state)
        return {"ok": True, "status": final_status, "lease": lease}

    def status(self) -> dict[str, Any]:
        self.reap()
        state = self._load()
        active = [x for x in state.get("leases", {}).values() if x.get("status") == "ACTIVE"]
        return {
            "ok": True,
            "active_count": len(active),
            "max_active": self.max_active,
            "leases": active,
        }
