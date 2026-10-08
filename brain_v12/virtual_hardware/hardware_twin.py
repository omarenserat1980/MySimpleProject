from __future__ import annotations

"""Server-level hardware twin registry.

Models observable server hardware/control surfaces while keeping a hard boundary
between simulated state and verified physical resources.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import uuid

from brain_v12.brain.evidence import EvidenceStore


class TruthState(str, Enum):
    SIMULATED = "SIMULATED"
    PROVISIONED = "PROVISIONED"
    VERIFIED = "VERIFIED"
    ATTACHED = "ATTACHED"
    RUNNING = "RUNNING"


class HealthState(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    OFFLINE = "OFFLINE"


class HardwareDomain(str, Enum):
    CHASSIS = "CHASSIS"
    MOTHERBOARD = "MOTHERBOARD"
    POWER = "POWER"
    COOLING = "COOLING"
    BMC = "BMC"
    CPU = "CPU"
    MEMORY = "MEMORY"
    PCIE = "PCIE"
    STORAGE = "STORAGE"
    NETWORK = "NETWORK"
    ACCELERATOR = "ACCELERATOR"
    FIRMWARE = "FIRMWARE"
    SECURITY = "SECURITY"


@dataclass
class Sensor:
    sensor_id: str
    kind: str
    value: float | int | str | bool
    unit: str | None = None
    health: HealthState = HealthState.UNKNOWN
    observed_at: float = field(default_factory=time.time)


@dataclass
class HardwareComponent:
    component_id: str
    domain: HardwareDomain
    model: str
    slot: str
    capacity: dict[str, Any] = field(default_factory=dict)
    capabilities: set[str] = field(default_factory=set)
    truth: TruthState = TruthState.SIMULATED
    health: HealthState = HealthState.UNKNOWN
    parent_id: str | None = None
    backend: str | None = None
    resource_ids: list[str] = field(default_factory=list)
    sensors: dict[str, Sensor] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HardwareRelation:
    source: str
    relation: str
    target: str
    metadata: dict[str, Any] = field(default_factory=dict)


class HardwareTwin:
    """Complete server-level hardware inventory and topology model."""

    def __init__(self, twin_id: str | None = None, name: str = "BRAIN-CLOUD-SERVER"):
        self.twin_id = twin_id or f"twin-{uuid.uuid4().hex[:16]}"
        self.name = name
        self.components: dict[str, HardwareComponent] = {}
        self.relations: list[HardwareRelation] = []
        self.events: list[dict[str, Any]] = []
        self.telemetry_seq = 0

    def add(self, component: HardwareComponent) -> HardwareComponent:
        if component.component_id in self.components:
            raise ValueError("TWIN_COMPONENT_EXISTS")
        self.components[component.component_id] = component
        self._event("COMPONENT_ADDED", component_id=component.component_id)
        return component

    def remove(self, component_id: str) -> None:
        component = self.components.get(component_id)
        if component is None:
            raise KeyError("TWIN_COMPONENT_NOT_FOUND")
        if component.resource_ids and component.truth in {TruthState.ATTACHED, TruthState.RUNNING}:
            raise RuntimeError("TWIN_COMPONENT_ATTACHED")
        del self.components[component_id]
        self.relations = [
            r for r in self.relations
            if r.source != component_id and r.target != component_id
        ]
        self._event("COMPONENT_REMOVED", component_id=component_id)

    def relate(self, source: str, relation: str, target: str, **metadata: Any) -> HardwareRelation:
        self._require(source)
        self._require(target)
        item = HardwareRelation(source, relation, target, metadata)
        self.relations.append(item)
        self._event("RELATION_ADDED", source=source, relation=relation, target=target)
        return item

    def bind_verified(
        self,
        component_id: str,
        resource_ids: list[str],
        evidence: dict[str, Any],
        backend: str,
    ) -> dict[str, Any]:
        component = self._require(component_id)
        if not resource_ids:
            raise ValueError("TWIN_EMPTY_RESOURCE_BINDING")
        if not evidence.get("verified"):
            raise RuntimeError("TWIN_EVIDENCE_NOT_VERIFIED")
        component.resource_ids = list(resource_ids)
        component.backend = backend
        component.truth = TruthState.ATTACHED
        component.metadata["evidence"] = dict(evidence)
        component.metadata["bound_at"] = time.time()
        self._event("COMPONENT_ATTACHED", component_id=component_id, backend=backend)
        return self.inspect(component_id)

    def bind_with_evidence_store(self, component_id: str, evidence_id: str,
                                evidence_store: EvidenceStore, backend: str) -> dict[str, Any]:
        component = self._require(component_id)
        record = evidence_store.get_valid(evidence_id, component_id, component.resource_ids or None)
        component.backend = backend
        component.truth = TruthState.ATTACHED
        component.metadata["evidence_id"] = record.evidence_id
        component.metadata["evidence_digest"] = record.digest
        component.metadata["verified_at"] = record.observed_at
        self._event("COMPONENT_ATTACHED", component_id=component_id, backend=backend,
                    evidence_id=record.evidence_id)
        return self.inspect(component_id)

    def mark_running(self, component_id: str, execution_id: str) -> dict[str, Any]:
        component = self._require(component_id)
        if component.truth != TruthState.ATTACHED:
            raise RuntimeError("TWIN_COMPONENT_NOT_ATTACHED")
        component.truth = TruthState.RUNNING
        component.metadata["execution_id"] = execution_id
        self._event("COMPONENT_RUNNING", component_id=component_id, execution_id=execution_id)
        return self.inspect(component_id)

    def mark_health(self, component_id: str, health: HealthState, reason: str | None = None) -> None:
        component = self._require(component_id)
        component.health = health
        if reason:
            component.metadata["health_reason"] = reason
        self._event("HEALTH_CHANGED", component_id=component_id, health=health.value)

    def record_sensor(
        self,
        component_id: str,
        sensor_id: str,
        kind: str,
        value: float | int | str | bool,
        unit: str | None = None,
        health: HealthState = HealthState.UNKNOWN,
    ) -> Sensor:
        component = self._require(component_id)
        self.telemetry_seq += 1
        sensor = Sensor(sensor_id, kind, value, unit, health, time.time())
        component.sensors[sensor_id] = sensor
        self._event(
            "TELEMETRY",
            sequence=self.telemetry_seq,
            component_id=component_id,
            sensor_id=sensor_id,
            value=value,
            unit=unit,
        )
        return sensor

    def health_summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for c in self.components.values():
            counts[c.health.value] = counts.get(c.health.value, 0) + 1
        return {
            "components": len(self.components),
            "health": counts,
            "failed": counts.get(HealthState.FAILED.value, 0),
            "offline": counts.get(HealthState.OFFLINE.value, 0),
        }

    def capacity_summary(self) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for c in self.components.values():
            for key, raw in c.capacity.items():
                if not isinstance(raw, (int, float)):
                    continue
                result.setdefault(key, {"simulated": 0.0, "verified": 0.0, "attached": 0.0})
                result[key]["simulated"] += float(raw)
                if c.truth in {TruthState.VERIFIED, TruthState.ATTACHED, TruthState.RUNNING}:
                    result[key]["verified"] += float(raw)
                if c.truth in {TruthState.ATTACHED, TruthState.RUNNING}:
                    result[key]["attached"] += float(raw)
        return result

    def topology(self) -> dict[str, Any]:
        return {
            "twin_id": self.twin_id,
            "name": self.name,
            "components": [self.inspect(cid) for cid in sorted(self.components)],
            "relations": [
                {"source": r.source, "relation": r.relation, "target": r.target, "metadata": r.metadata}
                for r in self.relations
            ],
        }

    def inspect(self, component_id: str) -> dict[str, Any]:
        c = self._require(component_id)
        return {
            "component_id": c.component_id,
            "domain": c.domain.value,
            "model": c.model,
            "slot": c.slot,
            "capacity": dict(c.capacity),
            "capabilities": sorted(c.capabilities),
            "truth": c.truth.value,
            "health": c.health.value,
            "parent_id": c.parent_id,
            "backend": c.backend,
            "resource_ids": list(c.resource_ids),
            "sensors": {
                k: {
                    "kind": s.kind,
                    "value": s.value,
                    "unit": s.unit,
                    "health": s.health.value,
                    "observed_at": s.observed_at,
                }
                for k, s in c.sensors.items()
            },
            "metadata": dict(c.metadata),
        }

    def _require(self, component_id: str) -> HardwareComponent:
        if component_id not in self.components:
            raise KeyError("TWIN_COMPONENT_NOT_FOUND")
        return self.components[component_id]

    def _event(self, kind: str, **data: Any) -> None:
        self.events.append({"ts": time.time(), "event": kind, **data})


def build_complete_server_twin(
    name: str = "BRAIN-CLOUD-SERVER",
    cpu_cores: int = 32,
    memory_gb: int = 128,
    storage_tb: float = 4,
    network_gbps: int = 25,
    gpu_count: int = 0,
) -> HardwareTwin:
    """Create a complete server-level topology without fabricating physical truth."""
    if min(cpu_cores, memory_gb, storage_tb, network_gbps) <= 0:
        raise ValueError("TWIN_INVALID_CAPACITY")
    twin = HardwareTwin(name=name)

    specs = [
        HardwareComponent("chassis0", HardwareDomain.CHASSIS, "rack-server", "rack:0"),
        HardwareComponent("board0", HardwareDomain.MOTHERBOARD, "server-board", "chassis:0"),
        HardwareComponent("psu0", HardwareDomain.POWER, "redundant-psu", "psu:0",
                          {"watts": 1200}, {"power-redundancy"}),
        HardwareComponent("cool0", HardwareDomain.COOLING, "fan-wall", "cooling:0",
                          {"fans": 6}, {"thermal-management"}),
        HardwareComponent("bmc0", HardwareDomain.BMC, "server-bmc", "management:0",
                          {}, {"redfish", "ipmi", "remote-power"}),
        HardwareComponent("cpu0", HardwareDomain.CPU, "x86-64-server-cpu", "socket:0",
                          {"cores": cpu_cores}, {"x86_64", "smt", "numa"}),
        HardwareComponent("mem0", HardwareDomain.MEMORY, "ecc-ddr5", "dimm-bank:0",
                          {"gb": memory_gb}, {"ecc", "numa"}),
        HardwareComponent("pcie0", HardwareDomain.PCIE, "pcie-root-complex", "pcie:root",
                          {}, {"mmio", "dma", "iommu", "msi-x"}),
        HardwareComponent("nvme0", HardwareDomain.STORAGE, "enterprise-nvme", "u.2:0",
                          {"tb": storage_tb}, {"nvme", "persistent", "smart"}),
        HardwareComponent("nic0", HardwareDomain.NETWORK, "ethernet-nic", "pci:net0",
                          {"gbps": network_gbps}, {"ethernet", "rss", "sriov"}),
        HardwareComponent("firmware0", HardwareDomain.FIRMWARE, "uefi", "firmware:0",
                          {}, {"uefi", "secure-boot", "acpi", "smbios"}),
        HardwareComponent("tpm0", HardwareDomain.SECURITY, "tpm-2.0", "security:0",
                          {}, {"tpm2", "attestation"}),
    ]
    for c in specs:
        twin.add(c)
    for i in range(gpu_count):
        twin.add(HardwareComponent(
            f"gpu{i}", HardwareDomain.ACCELERATOR, "gpu-accelerator", f"pci:gpu{i}",
            {"count": 1}, {"accelerator", "compute"},
        ))

    relations = [
        ("board0", "contains", "cpu0"),
        ("board0", "contains", "mem0"),
        ("board0", "contains", "pcie0"),
        ("board0", "contains", "firmware0"),
        ("board0", "contains", "tpm0"),
        ("pcie0", "connects", "nvme0"),
        ("pcie0", "connects", "nic0"),
        ("board0", "powers", "cpu0"),
        ("board0", "powers", "mem0"),
        ("cool0", "cools", "cpu0"),
        ("psu0", "powers", "board0"),
        ("bmc0", "manages", "board0"),
        ("bmc0", "manages", "psu0"),
        ("bmc0", "manages", "cool0"),
    ]
    for source, relation, target in relations:
        twin.relate(source, relation, target)
    for i in range(gpu_count):
        twin.relate("pcie0", "connects", f"gpu{i}")
    return twin
