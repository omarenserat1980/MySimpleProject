from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib, json
from typing import Any

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class Resource:
    id: str
    kind: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    state: str = "CREATED"
    created_at: str = field(default_factory=_now)

class AzureEmulator:
    """Deterministic Azure-shaped control plane; never contacts Azure."""
    def __init__(self, *, free_only: bool = True, quota: dict[str, int] | None = None):
        self.free_only = free_only
        self.quota = quota or {"vcpus": 8, "memory_mb": 16384, "storage_gb": 128}
        self.resources: dict[str, Resource] = {}
        self.evidence: list[dict[str, Any]] = []

    def _add(self, kind: str, name: str, properties: dict[str, Any] | None = None) -> Resource:
        rid = f"/subscriptions/emulated/resource/{kind}/{name}"
        if rid in self.resources:
            raise ValueError(f"resource already exists: {rid}")
        r = Resource(rid, kind, name, properties or {})
        self.resources[rid] = r
        return r

    def _usage(self) -> dict[str, int]:
        used = {"vcpus": 0, "memory_mb": 0, "storage_gb": 0}
        for r in self.resources.values():
            if r.kind == "vm" and r.state != "DELETED":
                used["vcpus"] += int(r.properties.get("vcpus", 0))
                used["memory_mb"] += int(r.properties.get("memory_mb", 0))
                used["storage_gb"] += int(r.properties.get("storage_gb", 0))
        return used

    def _gate_capacity(self, spec: dict[str, Any]) -> None:
        if not self.free_only:
            return
        usage = self._usage()
        projected = {k: usage[k] + int(spec.get(k, 0)) for k in usage}
        exceeded = [k for k in usage if projected[k] > self.quota[k]]
        if exceeded:
            raise RuntimeError(f"CAPACITY_GATE_FAILED:{','.join(exceeded)}")

    def create_resource_group(self, name: str) -> Resource:
        return self._add("resourceGroup", name, {"location": "emulated"})

    def create_network(self, name: str, address_space: str = "10.42.0.0/16") -> Resource:
        return self._add("vnet", name, {"address_space": address_space})

    def create_subnet(self, name: str, vnet: str, prefix: str = "10.42.0.0/24") -> Resource:
        return self._add("subnet", name, {"vnet": vnet, "prefix": prefix})

    def create_public_ip(self, name: str) -> Resource:
        return self._add("publicIp", name, {"address": "198.51.100.10"})

    def create_nic(self, name: str, subnet: str, public_ip: str) -> Resource:
        return self._add("nic", name, {"subnet": subnet, "public_ip": public_ip})

    def create_disk(self, name: str, size_gb: int = 64) -> Resource:
        return self._add("disk", name, {"size_gb": size_gb})

    def create_windows_server_2025_vm(self, name: str, *, vcpus: int = 2,
                                      memory_mb: int = 4096, storage_gb: int = 64,
                                      nic: str = "brain-nic") -> Resource:
        spec = {"vcpus": vcpus, "memory_mb": memory_mb, "storage_gb": storage_gb}
        self._gate_capacity(spec)
        vm = self._add("vm", name, {
            **spec, "os": "Windows Server 2025", "architecture": "x86_64",
            "nic": nic, "provider": "brain-emulated-azure",
        })
        vm.state = "RUNNING"
        return vm

    def health_evidence(self, vm_name: str) -> dict[str, Any]:
        vm = next((r for r in self.resources.values()
                   if r.kind == "vm" and r.name == vm_name), None)
        ok = bool(vm and vm.state == "RUNNING"
                  and vm.properties.get("os") == "Windows Server 2025"
                  and vm.properties.get("architecture") == "x86_64")
        evidence = {
            "schema": "BRAIN-AZURE-EMULATOR-EVIDENCE-1", "checked_at": _now(),
            "ok": ok, "provider": "brain-emulated-azure",
            "vm": asdict(vm) if vm else None, "usage": self._usage(), "quota": self.quota,
        }
        evidence["sha256"] = hashlib.sha256(
            json.dumps(evidence, sort_keys=True).encode()
        ).hexdigest()
        self.evidence.append(evidence)
        return evidence

    def export_state(self) -> dict[str, Any]:
        return {"schema": "BRAIN-AZURE-EMULATOR-STATE-1",
                "free_only": self.free_only, "quota": self.quota,
                "resources": [asdict(r) for r in self.resources.values()],
                "evidence": self.evidence}
