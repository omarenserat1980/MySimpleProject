"""Evidence-aware registry for virtual and physical Brain resources.

The fabric is deliberately an admission/control-plane layer. It does not discover
hardware by itself, start devices, or turn modeled capacity into host capacity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from time import time
from uuid import uuid4
from typing import Mapping


class RealityMode(str, Enum):
    PHYSICAL = "PHYSICAL"
    VIRTUAL = "VIRTUAL"
    HYBRID = "HYBRID"


class FabricError(ValueError):
    """Stable, safe-to-report fabric contract violation."""


@dataclass(frozen=True)
class ResourceEvidence:
    source: str
    evidence_id: str
    observed_at: float
    verified: bool = False


@dataclass(frozen=True)
class ResourceLease:
    lease_id: str
    resource_id: str
    task_id: str
    capacity: Mapping[str, float]
    created_at: float
    expires_at: float


@dataclass
class ResourceRecord:
    resource_id: str
    owner_id: str
    reality_mode: RealityMode
    capabilities: frozenset[str]
    modeled_capacity: dict[str, float] = field(default_factory=dict)
    measured_host_capacity: dict[str, float] = field(default_factory=dict)
    evidence: ResourceEvidence | None = None
    permissions: frozenset[str] = frozenset({"simulate"})
    metadata: dict[str, str] = field(default_factory=dict)
    leases: dict[str, ResourceLease] = field(default_factory=dict)

    def public(self, now: float | None = None, evidence_ttl_seconds: int = 120, trusted_evidence_sources: frozenset[str] = frozenset()) -> dict:
        now = time() if now is None else now
        evidence_fresh = bool(
            self.evidence
            and self.evidence.verified
            and self.evidence.source.strip()
            and self.evidence.source in trusted_evidence_sources
            and self.evidence.evidence_id.strip()
            and 0 <= now - self.evidence.observed_at <= evidence_ttl_seconds
        )
        return {
            "resource_id": self.resource_id,
            "owner_id": self.owner_id,
            "reality_mode": self.reality_mode.value,
            "capabilities": sorted(self.capabilities),
            "modeled_capacity": dict(self.modeled_capacity),
            "measured_host_capacity": dict(self.measured_host_capacity),
            "evidence": None if self.evidence is None else {
                "source": self.evidence.source,
                "evidence_id": self.evidence.evidence_id,
                "observed_at": self.evidence.observed_at,
                "verified": self.evidence.verified,
                "fresh": evidence_fresh,
            },
            "permissions": sorted(self.permissions),
            "active_leases": len(self.leases),
            "eligible_for_physical_work": (
                self.reality_mode in {RealityMode.PHYSICAL, RealityMode.HYBRID}
                and evidence_fresh
                and bool(self.measured_host_capacity)
                and "execute_physical" in self.permissions
            ),
            "execution_claim": (
                "REAL_DEVICE_EVIDENCE_REQUIRED"
                if self.reality_mode in {RealityMode.PHYSICAL, RealityMode.HYBRID}
                else "SIMULATION_ONLY"
            ),
        }


class HybridResourceFabric:
    """Thread-safe registry, evidence gate, and lease manager."""

    def __init__(self, evidence_ttl_seconds: int = 120, clock=time, trusted_evidence_sources: set[str] | frozenset[str] | None = None) -> None:
        if evidence_ttl_seconds < 1:
            raise FabricError("INVALID_EVIDENCE_TTL")
        self.evidence_ttl_seconds = evidence_ttl_seconds
        self._clock = clock
        # Fail closed by default: a caller-supplied `verified=True` is not enough.
        self._trusted_evidence_sources = frozenset(trusted_evidence_sources or ())
        self._lock = RLock()
        self._resources: dict[str, ResourceRecord] = {}
        self._task_leases: dict[str, str] = {}

    def register(self, record: ResourceRecord) -> dict:
        resource_id = record.resource_id.strip()
        owner_id = record.owner_id.strip()
        if not resource_id or not owner_id:
            raise FabricError("RESOURCE_ID_AND_OWNER_REQUIRED")
        if any(not k or not isinstance(v, (int, float)) or v < 0 for k, v in record.modeled_capacity.items()):
            raise FabricError("INVALID_MODELED_CAPACITY")
        if any(not k or not isinstance(v, (int, float)) or v < 0 for k, v in record.measured_host_capacity.items()):
            raise FabricError("INVALID_MEASURED_HOST_CAPACITY")
        # A physical identity must never be silently reclassified as virtual or vice versa.
        with self._lock:
            existing = self._resources.get(resource_id)
            if existing and (existing.owner_id != owner_id or existing.reality_mode != record.reality_mode):
                raise FabricError("RESOURCE_IDENTITY_CONFLICT")
            record.resource_id = resource_id
            record.owner_id = owner_id
            if existing:
                record.leases = existing.leases
            self._resources[resource_id] = record
            return {"ok": True, "status": "REGISTERED", "resource": record.public(self._clock(), self.evidence_ttl_seconds, self._trusted_evidence_sources)}

    def get(self, resource_id: str) -> dict:
        with self._lock:
            record = self._resources.get(resource_id)
            if record is None:
                return {"ok": False, "status": "RESOURCE_NOT_FOUND", "resource_id": resource_id}
            return {"ok": True, "resource": record.public(self._clock(), self.evidence_ttl_seconds, self._trusted_evidence_sources)}

    def list_resources(self) -> dict:
        with self._lock:
            values = [r.public(self._clock(), self.evidence_ttl_seconds, self._trusted_evidence_sources) for r in sorted(self._resources.values(), key=lambda x: x.resource_id)]
        return {"count": len(values), "resources": values}

    def reserve(
        self,
        resource_id: str,
        task_id: str,
        required_capacity: Mapping[str, float] | None = None,
        required_capabilities: set[str] | frozenset[str] | None = None,
        permission: str = "simulate",
        lease_seconds: int = 60,
        physical_execution: bool = False,
    ) -> dict:
        required_capacity = dict(required_capacity or {})
        required_capabilities = set(required_capabilities or ())
        if not task_id.strip() or lease_seconds < 1:
            raise FabricError("INVALID_TASK_OR_LEASE")
        if any(not k or not isinstance(v, (int, float)) or v < 0 for k, v in required_capacity.items()):
            raise FabricError("INVALID_REQUIRED_CAPACITY")
        now = self._clock()
        with self._lock:
            record = self._resources.get(resource_id)
            if record is None:
                return {"ok": False, "status": "RESOURCE_NOT_FOUND", "resource_id": resource_id}
            self._expire_leases(record, now)
            prior_resource = self._task_leases.get(task_id)
            if prior_resource:
                prior = self._resources.get(prior_resource)
                if prior and task_id in prior.leases:
                    lease = prior.leases[task_id]
                    if prior_resource == resource_id:
                        return {"ok": True, "status": "ALREADY_RESERVED", "lease": self._lease_public(lease)}
                    return {"ok": False, "status": "TASK_ALREADY_LEASED", "resource_id": prior_resource}
                self._task_leases.pop(task_id, None)

            status = record.public(now, self.evidence_ttl_seconds, self._trusted_evidence_sources)
            if physical_execution and not status["eligible_for_physical_work"]:
                return {"ok": False, "status": "PHYSICAL_EVIDENCE_GATE_BLOCKED", "resource_id": resource_id}
            if permission not in record.permissions:
                return {"ok": False, "status": "PERMISSION_DENIED", "resource_id": resource_id}
            if not required_capabilities.issubset(record.capabilities):
                return {"ok": False, "status": "CAPABILITY_MISMATCH", "resource_id": resource_id}
            capacity = record.measured_host_capacity if physical_execution else (
                record.modeled_capacity if record.reality_mode == RealityMode.VIRTUAL else record.measured_host_capacity
            )
            if not physical_execution and record.reality_mode == RealityMode.VIRTUAL:
                # Modeled resources are valid for simulation only, never physical execution.
                if permission != "simulate":
                    return {"ok": False, "status": "VIRTUAL_RESOURCE_SIMULATION_ONLY", "resource_id": resource_id}
            for key, amount in required_capacity.items():
                used = sum(lease.capacity.get(key, 0) for lease in record.leases.values())
                if amount + used > capacity.get(key, 0):
                    return {"ok": False, "status": "INSUFFICIENT_CAPACITY", "resource_id": resource_id, "dimension": key}
            lease = ResourceLease(
                lease_id=f"lease-{uuid4().hex}",
                resource_id=resource_id,
                task_id=task_id,
                capacity=required_capacity,
                created_at=now,
                expires_at=now + lease_seconds,
            )
            record.leases[task_id] = lease
            self._task_leases[task_id] = resource_id
            return {"ok": True, "status": "RESERVED", "lease": self._lease_public(lease)}

    def release(self, task_id: str) -> dict:
        with self._lock:
            resource_id = self._task_leases.pop(task_id, None)
            record = self._resources.get(resource_id) if resource_id else None
            lease = record.leases.pop(task_id, None) if record else None
            return {"ok": lease is not None, "status": "RELEASED" if lease else "NOT_RESERVED", "task_id": task_id}

    def _expire_leases(self, record: ResourceRecord, now: float) -> None:
        for task_id, lease in list(record.leases.items()):
            if lease.expires_at <= now:
                record.leases.pop(task_id, None)
                if self._task_leases.get(task_id) == record.resource_id:
                    self._task_leases.pop(task_id, None)

    @staticmethod
    def _lease_public(lease: ResourceLease) -> dict:
        return {
            "lease_id": lease.lease_id,
            "resource_id": lease.resource_id,
            "task_id": lease.task_id,
            "capacity": dict(lease.capacity),
            "created_at": lease.created_at,
            "expires_at": lease.expires_at,
        }
