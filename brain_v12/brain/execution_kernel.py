from __future__ import annotations

"""Brain execution kernel: one admission record across mission, lease and resources.

The kernel does not perform the work. It establishes the authority under which work
may execute. Every admitted execution receives a monotonically increasing fencing
epoch. Workers must present that epoch; stale workers are rejected.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import os
import time
from typing import Any


@dataclass(frozen=True)
class ExecutionEnvelope:
    execution_id: str
    intent_id: str
    fingerprint: str
    epoch: int
    owner: str
    admitted_at: float
    expires_at: float
    status: str = "ADMITTED"

    def public(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionKernel:
    def __init__(self, state_path: str | Path = ".brain/state/execution_kernel.json",
                 lease_seconds: int = 900) -> None:
        self.path = Path(state_path)
        self.lease_seconds = max(30, int(lease_seconds))

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"epoch": 0, "active": None, "history": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"epoch": 0, "active": None, "history": []}

    def _save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    @staticmethod
    def fingerprint(intent_id: str, operation: str,
                    payload: dict[str, Any] | None = None) -> str:
        raw = json.dumps({
            "intent_id": intent_id,
            "operation": operation,
            "payload": payload or {},
        }, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def admit(self, *, intent_id: str, operation: str, owner: str,
              payload: dict[str, Any] | None = None,
              capacity_admitted: bool = True) -> dict[str, Any]:
        if not intent_id or not operation or not owner:
            return {"ok": False, "status": "INVALID_EXECUTION_IDENTITY"}
        if not capacity_admitted:
            return {"ok": False, "status": "CAPACITY_BLOCKED"}

        state = self._load()
        now = time.time()
        active = state.get("active")
        if active and active.get("status") == "ADMITTED":
            if float(active.get("expires_at", 0)) > now:
                fp = self.fingerprint(intent_id, operation, payload)
                if active.get("fingerprint") == fp:
                    return {"ok": True, "status": "IDEMPOTENT_REUSE",
                            "envelope": active}
                return {"ok": False, "status": "EXECUTION_BUSY",
                        "active_execution": active.get("execution_id")}

        epoch = int(state.get("epoch", 0)) + 1
        fp = self.fingerprint(intent_id, operation, payload)
        execution_id = hashlib.sha256(
            f"{intent_id}:{fp}:{epoch}".encode("utf-8")
        ).hexdigest()[:24]
        envelope = ExecutionEnvelope(
            execution_id=execution_id,
            intent_id=intent_id,
            fingerprint=fp,
            epoch=epoch,
            owner=owner,
            admitted_at=now,
            expires_at=now + self.lease_seconds,
        )
        state["epoch"] = epoch
        state["active"] = envelope.public()
        state.setdefault("history", []).append(envelope.public())
        state["history"] = state["history"][-100:]
        self._save(state)
        return {"ok": True, "status": "ADMITTED", "envelope": envelope.public()}

    def validate(self, execution_id: str, epoch: int) -> dict[str, Any]:
        state = self._load()
        active = state.get("active")
        now = time.time()
        if not active:
            return {"ok": False, "status": "NO_ACTIVE_EXECUTION"}
        if active.get("execution_id") != execution_id:
            return {"ok": False, "status": "STALE_EXECUTION"}
        if int(active.get("epoch", -1)) != int(epoch):
            return {"ok": False, "status": "STALE_FENCING_EPOCH"}
        if active.get("status") != "ADMITTED":
            return {"ok": False, "status": "EXECUTION_NOT_ACTIVE"}
        if float(active.get("expires_at", 0)) <= now:
            return {"ok": False, "status": "EXECUTION_EXPIRED"}
        return {"ok": True, "status": "EXECUTION_AUTHORIZED",
                "execution_id": execution_id, "epoch": epoch}

    def heartbeat(self, execution_id: str, epoch: int) -> dict[str, Any]:
        check = self.validate(execution_id, epoch)
        if not check["ok"]:
            return check
        state = self._load()
        state["active"]["expires_at"] = time.time() + self.lease_seconds
        self._save(state)
        return {"ok": True, "status": "HEARTBEAT_ACCEPTED",
                "expires_at": state["active"]["expires_at"]}

    def finish(self, execution_id: str, epoch: int, status: str = "COMPLETED") -> dict[str, Any]:
        check = self.validate(execution_id, epoch)
        if not check["ok"]:
            return check
        state = self._load()
        state["active"]["status"] = status
        state["history"][-1]["status"] = status
        self._save(state)
        return {"ok": True, "status": status, "execution_id": execution_id, "epoch": epoch}

    def status(self) -> dict[str, Any]:
        state = self._load()
        active = state.get("active")
        return {
            "ok": True,
            "epoch": int(state.get("epoch", 0)),
            "active": active,
            "history_count": len(state.get("history", [])),
        }
