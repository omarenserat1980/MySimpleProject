"""Incremental ASIC resource factory built on the existing Brain ASIC adapter.

This first milestone intentionally supports ASIC simulator resources only. It reuses
ASICResourceAdapter, CapabilityRegistry, WorkerRegistry, HealthProbeEngine, TaskEngine,
and EvidenceStore rather than creating parallel registries or executors.
"""
from __future__ import annotations

from typing import Any

from .asic_resource_adapter import ASICResource, ASICResourceAdapter


MAX_SIMULATORS_PER_BATCH = 1000
LIFECYCLE = ("DISCOVERED", "REGISTERED", "VERIFIED", "AVAILABLE")


class ResourceFactory:
    """Create and lifecycle-manage many logical ASIC nodes with shared code."""

    def __init__(self, adapter: ASICResourceAdapter | None = None) -> None:
        self.adapter = adapter or ASICResourceAdapter()
        self._states: dict[str, str] = {}
        self._history: dict[str, list[str]] = {}
        self._reservations: dict[str, str] = {}
        self._task_resources: dict[str, str] = {}

    def create_asic_simulators(
        self,
        count: int,
        *,
        prefix: str = "ASIC-SIM",
        hashrate: float = 1.0,
        hashrate_unit: str = "H",
        power_watts: float = 0.0,
        power_cost: float = 0.0,
    ) -> dict[str, Any]:
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_SIMULATORS_PER_BATCH:
            raise ValueError("SIMULATOR_COUNT_OUT_OF_RANGE")
        prefix = str(prefix).strip()
        if not prefix or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in prefix):
            raise ValueError("INVALID_RESOURCE_PREFIX")
        ids = [f"{prefix}-{i:02d}" for i in range(1, count + 1)]
        duplicates = [rid for rid in ids if rid in self.adapter.resources]
        if duplicates:
            raise ValueError("RESOURCE_ALREADY_REGISTERED:" + ",".join(duplicates))
        # Validate all candidate resources before mutating the shared registry.
        candidates = [
            ASICResource(
                resource_id=rid,
                execution_mode="SIMULATOR",
                hashrate=hashrate,
                hashrate_unit=hashrate_unit,
                power_watts=power_watts,
                power_cost=power_cost,
                capabilities=("sha256d", "asic.simulate"),
                metadata={"factory": "ResourceFactory", "ordinal": i, "truth_level": "SIMULATED"},
            )
            for i, rid in enumerate(ids, start=1)
        ]
        created = []
        for resource in candidates:
            self._history[resource.resource_id] = ["DISCOVERED"]
            self.adapter.register(resource)
            self._history[resource.resource_id].append("REGISTERED")
            evidence = self.adapter.evidence.append(
                resource.resource_id,
                "resource_registration",
                {
                    "resource_id": resource.resource_id,
                    "resource_type": "ASIC",
                    "execution_mode": "SIMULATOR",
                    "truth_level": "SIMULATED",
                    "real_device": False,
                    "real_mining": False,
                    "revenue_verified": False,
                    "capabilities": list(resource.capabilities),
                },
                producer="brain.resource_factory",
            )
            checked = self.adapter.evidence.verify_hash(evidence["evidence_id"])
            if not checked.get("ok"):
                self._states[resource.resource_id] = "QUARANTINED"
                self._history[resource.resource_id].extend(["FAILED", "DIAGNOSED", "QUARANTINED"])
                raise RuntimeError("RESOURCE_EVIDENCE_INTEGRITY_FAILED")
            resource.evidence_ref = evidence["evidence_id"]
            self._history[resource.resource_id].append("VERIFIED")
            self._states[resource.resource_id] = "AVAILABLE"
            self._history[resource.resource_id].append("AVAILABLE")
            created.append(self.snapshot(resource.resource_id))
        return {
            "ok": True,
            "factory": "ASIC_SIMULATOR_FACTORY",
            "count": len(created),
            "resources": created,
            "truth_level": "SIMULATED",
            "real_device": False,
            "real_mining": False,
            "revenue_verified": False,
        }

    def reserve(self, resource_id: str, task_id: str) -> dict[str, Any]:
        self._require(resource_id)
        task_id = str(task_id).strip()
        if not task_id:
            raise ValueError("TASK_ID_REQUIRED")
        state = self._states[resource_id]
        if state == "QUARANTINED":
            return {"ok": False, "status": "BLOCKED_QUARANTINED", "resource_id": resource_id}
        if state != "AVAILABLE":
            return {"ok": False, "status": "RESOURCE_NOT_AVAILABLE", "resource_id": resource_id, "state": state}
        if task_id in self._task_resources:
            return {"ok": False, "status": "TASK_ALREADY_RESERVED", "task_id": task_id}
        self._states[resource_id] = "RESERVED"
        self._history[resource_id].append("RESERVED")
        self._reservations[resource_id] = task_id
        self._task_resources[task_id] = resource_id
        return {"ok": True, "status": "RESERVED", "resource_id": resource_id, "task_id": task_id}

    def begin(self, resource_id: str, task_id: str) -> dict[str, Any]:
        self._require(resource_id)
        if self._reservations.get(resource_id) != task_id or self._states[resource_id] != "RESERVED":
            return {"ok": False, "status": "RESERVATION_REQUIRED", "resource_id": resource_id}
        self._states[resource_id] = "BUSY"
        self._history[resource_id].append("BUSY")
        return {"ok": True, "status": "BUSY", "resource_id": resource_id, "task_id": task_id}

    def complete(self, resource_id: str, task_id: str) -> dict[str, Any]:
        self._require(resource_id)
        if self._reservations.get(resource_id) != task_id or self._states[resource_id] != "BUSY":
            return {"ok": False, "status": "ACTIVE_TASK_REQUIRED", "resource_id": resource_id}
        self._states[resource_id] = "COMPLETED"
        self._history[resource_id].append("COMPLETED")
        self._release_reservation(resource_id, task_id)
        return {"ok": True, "status": "COMPLETED", "resource_id": resource_id, "task_id": task_id}

    def fail_and_quarantine(self, resource_id: str, reason: str) -> dict[str, Any]:
        self._require(resource_id)
        task_id = self._reservations.get(resource_id)
        self._states[resource_id] = "FAILED"
        self._history[resource_id].append("FAILED")
        failure = self.adapter.evidence.append(
            resource_id, "resource_failure",
            {"resource_id": resource_id, "reason": str(reason), "truth_level": "SIMULATED"},
            producer="brain.resource_factory",
        )
        self._history[resource_id].append("DIAGNOSED")
        self._states[resource_id] = "QUARANTINED"
        self._history[resource_id].append("QUARANTINED")
        if task_id:
            self._release_reservation(resource_id, task_id)
        return {"ok": True, "status": "QUARANTINED", "resource_id": resource_id, "failure_evidence_ref": failure["evidence_id"]}

    def recover(self, resource_id: str) -> dict[str, Any]:
        resource = self._require(resource_id)
        if self._states[resource_id] != "QUARANTINED":
            return {"ok": False, "status": "NOT_QUARANTINED", "resource_id": resource_id}
        self._states[resource_id] = "RECOVERY"
        self._history[resource_id].append("RECOVERY")
        checked = self.adapter.evidence.verify_hash(resource.evidence_ref) if resource.evidence_ref else {"ok": False}
        if not checked.get("ok"):
            self._states[resource_id] = "QUARANTINED"
            self._history[resource_id].append("QUARANTINED")
            return {"ok": False, "status": "RECOVERY_BLOCKED_EVIDENCE_INVALID", "resource_id": resource_id}
        self._history[resource_id].append("VERIFY")
        self._states[resource_id] = "AVAILABLE"
        self._history[resource_id].append("AVAILABLE")
        return {"ok": True, "status": "AVAILABLE", "resource_id": resource_id}

    def snapshot(self, resource_id: str) -> dict[str, Any]:
        resource = self._require(resource_id)
        return {
            "resource_id": resource_id,
            "resource_type": "ASIC",
            "execution_mode": "SIMULATOR",
            "state": self._states[resource_id],
            "lifecycle_history": list(self._history[resource_id]),
            "capabilities": list(resource.capabilities),
            "hashrate": resource.hashrate,
            "hashrate_unit": resource.hashrate_unit,
            "power_watts": resource.power_watts,
            "health": resource.health_status,
            "verification_state": resource.verification_status,
            "truth_level": "SIMULATED",
            "evidence_ref": resource.evidence_ref,
            "economics_state": "NOT_REVENUE",
            "real_device": False,
            "real_mining": False,
            "revenue_verified": False,
        }

    def _require(self, resource_id: str) -> ASICResource:
        try:
            return self.adapter.resources[resource_id]
        except KeyError as exc:
            raise KeyError("RESOURCE_NOT_FOUND") from exc

    def _release_reservation(self, resource_id: str, task_id: str) -> None:
        self._reservations.pop(resource_id, None)
        self._task_resources.pop(task_id, None)
