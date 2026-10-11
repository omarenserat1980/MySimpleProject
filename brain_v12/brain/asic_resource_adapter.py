"""Evidence-first ASIC resource integration for Brain V12.

SIMULATOR records are estimates only. Remote and physical resources are
registered as unverified until externally supplied, hash-verified telemetry
is recorded. This adapter never connects to a provider, starts mining, or
handles wallet credentials.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import math
from typing import Any

from .capability_registry import CapabilityRegistry
from .evidence_store import EvidenceStore
from .health_probe import HealthProbeEngine
from .mining_engine import MiningEngine
from .task_engine import TaskEngine
from .worker_registry import WorkerRegistry


EXECUTION_MODES = frozenset({"SIMULATOR", "REMOTE_PROVIDER", "PHYSICAL_DEVICE"})
REAL_MODES = frozenset({"REMOTE_PROVIDER", "PHYSICAL_DEVICE"})


@dataclass
class ASICResource:
    resource_id: str
    resource_type: str = "ASIC"
    execution_mode: str = "SIMULATOR"
    provider: str | None = None
    device_model: str | None = None
    capabilities: tuple[str, ...] = ("sha256d", "asic.simulate")
    hashrate: float = 0.0
    hashrate_unit: str = "TH"
    power_watts: float = 0.0
    power_cost: float = 0.0
    pool_status: str = "NOT_CONNECTED"
    heartbeat: str | None = None
    health_status: str = "UNKNOWN"
    verification_status: str = "UNVERIFIED"
    evidence_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.resource_id.strip():
            raise ValueError("RESOURCE_ID_REQUIRED")
        if self.resource_type != "ASIC":
            raise ValueError("RESOURCE_TYPE_MUST_BE_ASIC")
        if self.execution_mode not in EXECUTION_MODES:
            raise ValueError("INVALID_EXECUTION_MODE")
        if not math.isfinite(float(self.hashrate)) or self.hashrate < 0:
            raise ValueError("INVALID_HASHRATE")
        if not math.isfinite(float(self.power_watts)) or self.power_watts < 0:
            raise ValueError("INVALID_POWER_WATTS")
        if not math.isfinite(float(self.power_cost)) or self.power_cost < 0:
            raise ValueError("INVALID_POWER_COST")
        if self.execution_mode == "SIMULATOR":
            # Simulator data never inherits real-device verification or pool claims.
            self.verification_status = "SIMULATED"
            self.pool_status = "NOT_CONNECTED"
            self.evidence_ref = None
        else:
            self.verification_status = "UNVERIFIED"


class ASICResourceAdapter:
    """Registry, capability selector, simulation, health and evidence bridge."""

    def __init__(self, *, registry: CapabilityRegistry | None = None,
                 tasks: TaskEngine | None = None,
                 health: HealthProbeEngine | None = None,
                 evidence: EvidenceStore | None = None,
                 mining: MiningEngine | None = None,
                 workers: WorkerRegistry | None = None) -> None:
        self.registry = registry or CapabilityRegistry()
        self.tasks = tasks or TaskEngine()
        self.health = health or HealthProbeEngine()
        self.evidence = evidence or EvidenceStore(":memory:")
        self.mining = mining or MiningEngine()
        self.workers = workers or WorkerRegistry()
        self.resources: dict[str, ASICResource] = {}

    def register(self, resource: ASICResource) -> dict[str, Any]:
        if resource.resource_id in self.resources:
            raise ValueError("RESOURCE_ALREADY_REGISTERED")
        self.resources[resource.resource_id] = resource
        executor_id = f"asic:{resource.resource_id}"
        capabilities = set(resource.capabilities)
        if resource.execution_mode == "SIMULATOR":
            capabilities.add("asic.simulate")
        else:
            capabilities.discard("asic.simulate")
        self.registry.register(executor_id, capabilities, {
            "resource_id": resource.resource_id,
            "resource_type": "ASIC",
            "execution_mode": resource.execution_mode,
            "verification_status": resource.verification_status,
        })
        self.workers.register(executor_id, resource.execution_mode.lower(), capabilities)
        self.health.register(executor_id, lambda rid=resource.resource_id: self._health_probe(rid))
        return self.resource_snapshot(resource.resource_id)

    def select(self, required_capabilities: set[str] | tuple[str, ...] = ()) -> list[dict[str, Any]]:
        selected = self.registry.select(required_capabilities)
        result = []
        for item in selected:
            resource_id = item.metadata["resource_id"]
            health = self.check_health(resource_id)
            if health["available"]:
                result.append({**asdict(item), "health_status": health["health_status"]})
            else:
                self.registry.offline(item.executor_id)
        return result

    def _health_probe(self, resource_id: str) -> dict[str, Any]:
        resource = self.resources[resource_id]
        if resource.execution_mode == "SIMULATOR":
            return {"available": True, "reason": "SIMULATION_ONLY", "execution_mode": "SIMULATOR"}
        if not resource.heartbeat:
            return {"available": False, "reason": "HEARTBEAT_MISSING", "execution_mode": resource.execution_mode}
        try:
            heartbeat = datetime.fromisoformat(resource.heartbeat.replace("Z", "+00:00"))
            if heartbeat.tzinfo is None:
                return {"available": False, "reason": "HEARTBEAT_TIMEZONE_REQUIRED"}
            age = (datetime.now(timezone.utc) - heartbeat.astimezone(timezone.utc)).total_seconds()
        except (TypeError, ValueError):
            return {"available": False, "reason": "HEARTBEAT_INVALID"}
        return {"available": 0 <= age <= 120, "reason": "FRESH_HEARTBEAT" if 0 <= age <= 120 else "HEARTBEAT_STALE", "heartbeat_age_seconds": round(age, 2)}

    def check_health(self, resource_id: str) -> dict[str, Any]:
        resource = self._require_resource(resource_id)
        result = self.health.probe(f"asic:{resource_id}")
        resource.health_status = (
            "SIMULATED" if resource.execution_mode == "SIMULATOR"
            else ("AVAILABLE_UNVERIFIED" if result.available else "UNHEALTHY_UNVERIFIED")
        )
        return {"resource_id": resource_id, **asdict(result),
                "health_status": resource.health_status,
                "verification_status": resource.verification_status}

    def simulate(self, resource_id: str, *, duration_seconds: int = 60) -> dict[str, Any]:
        resource = self._require_resource(resource_id)
        if resource.execution_mode != "SIMULATOR":
            raise PermissionError("SIMULATION_MODE_REQUIRED")
        if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int) or duration_seconds <= 0:
            raise ValueError("DURATION_SECONDS_MUST_BE_POSITIVE_INTEGER")
        task = self.tasks.create(f"Simulate ASIC {resource_id}")
        self.tasks.update(task["id"], "RUNNING")
        hashrate_hs = self.mining.normalize_hashrate(resource.hashrate, resource.hashrate_unit)
        payload = {
            "resource_id": resource_id,
            "resource_type": "ASIC",
            "execution_mode": "SIMULATOR",
            "duration_seconds": duration_seconds,
            "input_hashrate": resource.hashrate,
            "input_hashrate_unit": resource.hashrate_unit,
            "estimated_hashes": int(hashrate_hs * duration_seconds),
            "power_watts": resource.power_watts,
            "pool_status": "NOT_CONNECTED",
            "real_device_measurement": False,
            "revenue_verified": False,
        }
        evidence = self.evidence.append(task["id"], "asic_simulation", payload, producer="brain.asic_resource_adapter")
        verification = self.evidence.verify_hash(evidence["evidence_id"])
        self.tasks.verify_and_complete(task["id"], verification, evidence["evidence_id"])
        return {"task": self.tasks.tasks[task["id"]], "result": payload,
                "evidence_ref": evidence["evidence_id"], "evidence_sha256": evidence["sha256"],
                "evidence_verification": verification["status"]}

    def record_telemetry(self, resource_id: str, telemetry: dict[str, Any]) -> dict[str, Any]:
        resource = self._require_resource(resource_id)
        if resource.execution_mode not in REAL_MODES:
            raise PermissionError("REAL_RESOURCE_MODE_REQUIRED")
        if not isinstance(telemetry, dict) or not telemetry:
            raise ValueError("TELEMETRY_REQUIRED")
        # Measurements are caller supplied. No connection or identity attestation is implied.
        payload = {"resource_id": resource_id, "execution_mode": resource.execution_mode,
                   "source": "externally_supplied_untrusted_telemetry", "telemetry": telemetry}
        evidence = self.evidence.append(resource_id, "asic_telemetry", payload, producer="brain.asic_resource_adapter")
        checked = self.evidence.verify_hash(evidence["evidence_id"])
        resource.evidence_ref = evidence["evidence_id"]
        resource.verification_status = "EVIDENCE_HASH_VERIFIED_UNATTESTED" if checked.get("ok") else "UNVERIFIED"
        resource.heartbeat = str(telemetry.get("heartbeat") or "") or None
        resource.pool_status = str(telemetry.get("pool_status") or "UNKNOWN")
        resource.health_status = "UNVERIFIED"
        capabilities = set(resource.capabilities)
        capabilities.discard("asic.simulate")
        self.registry.register(f"asic:{resource_id}", capabilities, {
            "resource_id": resource_id, "resource_type": "ASIC",
            "execution_mode": resource.execution_mode,
            "verification_status": resource.verification_status,
        })
        self.workers.heartbeat(f"asic:{resource_id}", capabilities)
        return {"evidence_ref": resource.evidence_ref, "verification_status": resource.verification_status,
                "external_identity_verified": False, "evidence_sha256": evidence["sha256"]}

    def analyze_economics(self, resource_id: str, *, electricity_jod_per_kwh: float | None = None,
                          gross_revenue_jod_per_day: float, pool_fee_percent: float = 0.0,
                          other_daily_cost_jod: float = 0.0) -> dict[str, Any]:
        resource = self._require_resource(resource_id)
        electricity_cost = resource.power_cost if electricity_jod_per_kwh is None else electricity_jod_per_kwh
        result = self.mining.analyze({
            "algorithm": "sha256d", "hashrate": resource.hashrate,
            "hashrate_unit": resource.hashrate_unit, "power_watts": resource.power_watts,
            "electricity_jod_per_kwh": electricity_cost,
            "gross_revenue_jod_per_day": gross_revenue_jod_per_day,
            "pool_fee_percent": pool_fee_percent, "other_daily_cost_jod": other_daily_cost_jod,
        })
        result.update({"resource_id": resource_id, "execution_mode": resource.execution_mode,
                       "resource_verification_status": resource.verification_status,
                       "actual_revenue_verified": False})
        return result

    def release_gate(self, resource_id: str) -> dict[str, Any]:
        resource = self._require_resource(resource_id)
        failures = []
        if resource.execution_mode == "SIMULATOR":
            failures.append("SIMULATOR_CANNOT_PROVE_REAL_RESOURCE")
        if resource.execution_mode in REAL_MODES and not resource.evidence_ref:
            failures.append("TELEMETRY_EVIDENCE_REQUIRED")
        evidence = self.evidence.get(resource.evidence_ref) if resource.evidence_ref else None
        checked = self.evidence.verify_hash(resource.evidence_ref) if resource.evidence_ref else {"ok": False}
        if resource.execution_mode in REAL_MODES and (not evidence or evidence.get("kind") != "asic_telemetry"):
            failures.append("REAL_TELEMETRY_EVIDENCE_REQUIRED")
        if resource.execution_mode in REAL_MODES and not checked.get("ok"):
            failures.append("EVIDENCE_INTEGRITY_FAILED")
        # Hash integrity alone does not prove provider or device identity.
        failures.append("EXTERNAL_IDENTITY_ATTESTATION_REQUIRED")
        return {"status": "BLOCKED" if failures else "READY_FOR_REVIEW", "resource_id": resource_id,
                "execution_mode": resource.execution_mode, "failures": failures,
                "publish_or_activate": False, "external_identity_verified": False}

    def resource_snapshot(self, resource_id: str) -> dict[str, Any]:
        return asdict(self._require_resource(resource_id))

    def snapshot(self) -> dict[str, Any]:
        return {"resources": [asdict(r) for r in self.resources.values()],
                "capabilities": self.registry.status(), "resource_registry": self.workers.snapshot(),
                "health": self.health.snapshot(),
                "execution": "SIMULATION_OR_EXTERNALLY_SUPPLIED_TELEMETRY_ONLY",
                "network_access": False, "mining_started": False}

    def _require_resource(self, resource_id: str) -> ASICResource:
        try:
            return self.resources[resource_id]
        except KeyError as exc:
            raise KeyError("ASIC_RESOURCE_NOT_FOUND") from exc
