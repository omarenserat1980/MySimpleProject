from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class DriftKind(str, Enum):
    NONE = "NONE"
    CAPACITY = "CAPACITY_DRIFT"
    IDENTITY = "IDENTITY_DRIFT"
    TOPOLOGY = "TOPOLOGY_DRIFT"
    HEALTH = "HEALTH_DRIFT"
    ATTACHMENT = "ATTACHMENT_DRIFT"
    STALE = "STALE"

@dataclass(frozen=True)
class Observation:
    component_id: str
    identity: str | None
    capacity: dict[str, Any]
    health: str
    attached: bool

class HardwareReconciler:
    """Compare desired twin state with fresh provider observations."""

    def __init__(self, stale_after_seconds: float = 120.0):
        self.stale_after_seconds = float(stale_after_seconds)

    def compare(self, desired: dict[str, Any], observed: Observation | None,
                observed_at: float | None = None, now: float | None = None) -> dict[str, Any]:
        import time
        now = time.time() if now is None else now
        if observed is None or observed_at is None or now - observed_at > self.stale_after_seconds:
            return {"ok": False, "status": "STALE", "drift": DriftKind.STALE.value}
        if desired.get("identity") and observed.identity and desired["identity"] != observed.identity:
            return {"ok": False, "status": "QUARANTINE", "drift": DriftKind.IDENTITY.value}
        if desired.get("capacity") != observed.capacity:
            return {"ok": False, "status": "RECONCILE", "drift": DriftKind.CAPACITY.value,
                    "desired": desired.get("capacity"), "observed": observed.capacity}
        if desired.get("health") and desired["health"] != observed.health:
            return {"ok": False, "status": "RECONCILE", "drift": DriftKind.HEALTH.value}
        if bool(desired.get("attached")) != observed.attached:
            return {"ok": False, "status": "RECONCILE", "drift": DriftKind.ATTACHMENT.value}
        return {"ok": True, "status": "IN_SYNC", "drift": DriftKind.NONE.value}

    def reconcile_plan(self, comparison: dict[str, Any]) -> dict[str, Any]:
        drift = comparison.get("drift", DriftKind.NONE.value)
        actions = {
            DriftKind.NONE.value: [],
            DriftKind.STALE.value: ["MARK_STALE", "STOP_NEW_ADMISSIONS"],
            DriftKind.IDENTITY.value: ["QUARANTINE", "FENCE", "REQUEST_REATTESTATION"],
            DriftKind.CAPACITY.value: ["REFRESH_RESOURCE_CAPACITY", "VERIFY"],
            DriftKind.HEALTH.value: ["MARK_DEGRADED", "VERIFY"],
            DriftKind.ATTACHMENT.value: ["RECONCILE_ATTACHMENT", "VERIFY"],
        }.get(drift, ["QUARANTINE"])
        return {"ok": comparison.get("status") != "QUARANTINE",
                "status": "ACTION_REQUIRED" if actions else "IN_SYNC",
                "actions": actions, "drift": drift}
