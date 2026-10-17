"""Brain-owned logical cloud provider registry.

The Brain control plane can expose provider-like inventory and scheduling
metadata for enrolled workers. It cannot manufacture CPU/RAM/storage: capacity
is advertised only for externally backed, authenticated, fresh worker records.
This module is intentionally read-only and never provisions infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True)
class WorkerRecord:
    worker_id: str
    provider_instance_id: str
    cpu_cores: int
    memory_gib: float
    storage_gib: int
    authenticated: bool
    heartbeat_at: str
    physical_or_cloud_backed: bool
    verified_zero_cost: bool
    authorized: bool


def _fresh(heartbeat_at: str, now: datetime, max_age_seconds: int) -> bool:
    try:
        stamp = datetime.fromisoformat(heartbeat_at.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return False
        age = (now - stamp.astimezone(timezone.utc)).total_seconds()
        return 0 <= age <= max_age_seconds
    except (TypeError, ValueError):
        return False


def brain_provider_inventory(
    workers: Iterable[WorkerRecord],
    *,
    now: datetime | None = None,
    max_heartbeat_age_seconds: int = 180,
) -> dict:
    """Expose only verified, authorized, fresh worker capacity; never create nodes."""
    current = now or datetime.now(timezone.utc)
    if max_heartbeat_age_seconds < 1:
        raise ValueError("INVALID_HEARTBEAT_MAX_AGE")

    accepted = []
    rejected = []
    for worker in workers:
        reasons = []
        if not worker.worker_id.strip():
            reasons.append("WORKER_ID_MISSING")
        if not worker.provider_instance_id.strip():
            reasons.append("PROVIDER_INSTANCE_ID_MISSING")
        if not worker.authenticated:
            reasons.append("AUTHENTICATION_UNVERIFIED")
        if not worker.authorized:
            reasons.append("OWNER_AUTHORIZATION_MISSING")
        if not worker.physical_or_cloud_backed:
            reasons.append("NO_REAL_BACKING_RESOURCE")
        if not worker.verified_zero_cost:
            reasons.append("ZERO_COST_UNVERIFIED")
        if not _fresh(worker.heartbeat_at, current, max_heartbeat_age_seconds):
            reasons.append("HEARTBEAT_STALE_OR_INVALID")
        if worker.cpu_cores < 1 or worker.memory_gib <= 0 or worker.storage_gib < 1:
            reasons.append("CAPACITY_INVALID")
        if reasons:
            rejected.append({"worker_id": worker.worker_id or None, "reasons": reasons})
            continue
        accepted.append({
            "worker_id": worker.worker_id,
            "provider_instance_id": worker.provider_instance_id,
            "cpu_cores": worker.cpu_cores,
            "memory_gib": worker.memory_gib,
            "storage_gib": worker.storage_gib,
            "heartbeat_at": worker.heartbeat_at,
        })

    return {
        "provider": "brain-cloud",
        "mode": "BRAIN_OWNED_CONTROL_PLANE",
        "status": "CAPACITY_AVAILABLE" if accepted else "NO_VERIFIED_CAPACITY",
        "workers": accepted,
        "rejected_workers": rejected,
        "worker_count": len(accepted),
        "provisioning_supported": False,
        "capacity_is_manufactured": False,
        "next_step": (
            "Route only bounded tasks to an enrolled worker using the existing executor contract."
            if accepted
            else "Enroll a real authorized worker through a provider adapter; this control plane cannot create compute by itself."
        ),
    }
