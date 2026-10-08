from __future__ import annotations

"""Deep virtual hardware machine for Brain.

This layer models hardware topology and machine state. It never claims that
virtual capacity is physical capacity. A backend/attachment must provide real
resources before execution is admitted.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import hashlib
import time
import uuid


class DeviceState(str, Enum):
    ABSENT = "ABSENT"
    PRESENT = "PRESENT"
    ATTACHED = "ATTACHED"
    FAULTED = "FAULTED"


class MachineState(str, Enum):
    CREATED = "CREATED"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    FAULTED = "FAULTED"


@dataclass(frozen=True)
class VirtualDeviceSpec:
    device_id: str
    device_type: str
    slot: str
    capacity: dict[str, Any] = field(default_factory=dict)
    capabilities: tuple[str, ...] = ()
    backend: str | None = None


@dataclass
class VirtualHardwareMachine:
    """A motherboard-level virtual machine model.

    It provides deterministic topology, device state, MMIO/IRQ bookkeeping,
    firmware state, snapshots and a strict physical-capacity boundary.
    """

    name: str
    architecture: str = "x86_64"
    firmware: str = "UEFI"
    machine_type: str = "BRAIN-PC-V1"
    state: MachineState = MachineState.CREATED
    devices: dict[str, VirtualDeviceSpec] = field(default_factory=dict)
    device_state: dict[str, DeviceState] = field(default_factory=dict)
    mmio: dict[str, dict[str, Any]] = field(default_factory=dict)
    irq_routes: dict[int, str] = field(default_factory=dict)
    boot_order: list[str] = field(default_factory=lambda: ["disk", "network"])
    physical_bindings: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    boot_count: int = 0
    created_at: float = field(default_factory=time.time)

    def add_device(self, spec: VirtualDeviceSpec) -> dict[str, Any]:
        if spec.device_id in self.devices:
            raise ValueError("VHW_DEVICE_EXISTS")
        if spec.slot in {d.slot for d in self.devices.values()}:
            raise ValueError("VHW_SLOT_OCCUPIED")
        self.devices[spec.device_id] = spec
        self.device_state[spec.device_id] = DeviceState.PRESENT
        self._event("DEVICE_ADDED", device_id=spec.device_id, type=spec.device_type)
        return self.inspect_device(spec.device_id)

    def remove_device(self, device_id: str) -> None:
        if device_id not in self.devices:
            raise KeyError("VHW_DEVICE_NOT_FOUND")
        if device_id in self.physical_bindings:
            raise RuntimeError("VHW_DEVICE_PHYSICALLY_BOUND")
        del self.devices[device_id]
        self.device_state.pop(device_id, None)
        self.mmio.pop(device_id, None)
        for irq, owner in list(self.irq_routes.items()):
            if owner == device_id:
                del self.irq_routes[irq]
        self._event("DEVICE_REMOVED", device_id=device_id)

    def map_mmio(self, device_id: str, base: int, size: int) -> dict[str, Any]:
        self._require_device(device_id)
        if base < 0 or size <= 0:
            raise ValueError("VHW_INVALID_MMIO")
        end = base + size
        for region in self.mmio.values():
            if base < region["end"] and end > region["base"]:
                raise ValueError("VHW_MMIO_OVERLAP")
        self.mmio[device_id] = {"base": base, "size": size, "end": end}
        self._event("MMIO_MAPPED", device_id=device_id, base=base, size=size)
        return dict(self.mmio[device_id])

    def route_irq(self, irq: int, device_id: str) -> dict[str, Any]:
        self._require_device(device_id)
        if irq < 0:
            raise ValueError("VHW_INVALID_IRQ")
        if irq in self.irq_routes and self.irq_routes[irq] != device_id:
            raise ValueError("VHW_IRQ_OCCUPIED")
        self.irq_routes[irq] = device_id
        self._event("IRQ_ROUTED", irq=irq, device_id=device_id)
        return {"irq": irq, "device_id": device_id}

    def bind_physical(
        self,
        device_id: str,
        provider_id: str,
        resource_ids: list[str],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Bind a virtual device to already-admitted real resources.

        Binding never creates capacity. The caller must supply evidence from
        Resource Fabric / Execution Kernel admission.
        """
        self._require_device(device_id)
        if not resource_ids:
            raise ValueError("VHW_EMPTY_PHYSICAL_BINDING")
        if not evidence.get("verified"):
            raise RuntimeError("VHW_BINDING_REQUIRES_VERIFIED_EVIDENCE")
        self.physical_bindings[device_id] = {
            "provider_id": provider_id,
            "resource_ids": list(resource_ids),
            "evidence": dict(evidence),
            "bound_at": time.time(),
        }
        self.device_state[device_id] = DeviceState.ATTACHED
        self._event("PHYSICAL_BOUND", device_id=device_id, provider_id=provider_id)
        return dict(self.physical_bindings[device_id])

    def unbind_physical(self, device_id: str) -> None:
        self.physical_bindings.pop(device_id, None)
        if device_id in self.devices:
            self.device_state[device_id] = DeviceState.PRESENT
        self._event("PHYSICAL_UNBOUND", device_id=device_id)

    def start(self, physical_capacity_verified: bool = False) -> dict[str, Any]:
        if not physical_capacity_verified:
            raise RuntimeError("VHW_CAPACITY_NOT_VERIFIED")
        if self.state == MachineState.RUNNING:
            return self.status()
        if self.state == MachineState.FAULTED:
            raise RuntimeError("VHW_MACHINE_FAULTED")
        self.state = MachineState.RUNNING
        self.boot_count += 1
        self._event("POWER_ON", boot_count=self.boot_count)
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.state = MachineState.STOPPED
        self._event("POWER_OFF")
        return self.status()

    def pause(self) -> dict[str, Any]:
        if self.state != MachineState.RUNNING:
            raise RuntimeError("VHW_NOT_RUNNING")
        self.state = MachineState.PAUSED
        self._event("PAUSED")
        return self.status()

    def resume(self) -> dict[str, Any]:
        if self.state != MachineState.PAUSED:
            raise RuntimeError("VHW_NOT_PAUSED")
        self.state = MachineState.RUNNING
        self._event("RESUMED")
        return self.status()

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "architecture": self.architecture,
            "firmware": self.firmware,
            "machine_type": self.machine_type,
            "state": self.state.value,
            "devices": {
                k: {
                    "spec": {
                        "device_id": v.device_id,
                        "device_type": v.device_type,
                        "slot": v.slot,
                        "capacity": v.capacity,
                        "capabilities": list(v.capabilities),
                        "backend": v.backend,
                    },
                    "state": self.device_state[k].value,
                }
                for k, v in self.devices.items()
            },
            "mmio": self.mmio,
            "irq_routes": {str(k): v for k, v in self.irq_routes.items()},
            "boot_order": list(self.boot_order),
            "physical_bindings": self.physical_bindings,
        }

    def identity(self) -> str:
        raw = f"{self.name}|{self.architecture}|{self.machine_type}|{sorted(self.devices)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def status(self) -> dict[str, Any]:
        physical = sum(bool(v) for v in self.physical_bindings.values())
        return {
            "ok": True,
            "name": self.name,
            "identity": self.identity(),
            "state": self.state.value,
            "architecture": self.architecture,
            "firmware": self.firmware,
            "machine_type": self.machine_type,
            "device_count": len(self.devices),
            "attached_devices": physical,
            "unbound_devices": len(self.devices) - physical,
            "mmio_regions": len(self.mmio),
            "irq_routes": len(self.irq_routes),
            "boot_count": self.boot_count,
            "capacity_truth": "VIRTUAL_UNTIL_VERIFIED",
        }

    def inspect_device(self, device_id: str) -> dict[str, Any]:
        self._require_device(device_id)
        spec = self.devices[device_id]
        return {
            "device_id": spec.device_id,
            "device_type": spec.device_type,
            "slot": spec.slot,
            "capacity": dict(spec.capacity),
            "capabilities": list(spec.capabilities),
            "backend": spec.backend,
            "state": self.device_state[device_id].value,
            "physical_binding": self.physical_bindings.get(device_id),
            "mmio": self.mmio.get(device_id),
            "irq": next((i for i, d in self.irq_routes.items() if d == device_id), None),
        }

    def _require_device(self, device_id: str) -> None:
        if device_id not in self.devices:
            raise KeyError("VHW_DEVICE_NOT_FOUND")

    def _event(self, kind: str, **data: Any) -> None:
        self.events.append({"ts": time.time(), "event": kind, **data})


def build_brain_server(
    name: str = "BRAIN-VSERVER-01",
    vcpu: int = 8,
    memory_gb: int = 16,
    storage_gb: int = 256,
    gpu: bool = False,
) -> VirtualHardwareMachine:
    """Compose a complete virtual server motherboard."""
    if min(vcpu, memory_gb, storage_gb) <= 0:
        raise ValueError("VHW_INVALID_SERVER_CAPACITY")

    m = VirtualHardwareMachine(name=name)
    m.add_device(VirtualDeviceSpec(
        "cpu0", "VCPU", "cpu:0",
        {"cores": vcpu}, ("compute", "x86_64")
    ))
    m.add_device(VirtualDeviceSpec(
        "ram0", "VRAM_MEMORY", "memory:0",
        {"gb": memory_gb}, ("memory",)
    ))
    m.add_device(VirtualDeviceSpec(
        "disk0", "VNVME", "storage:0",
        {"gb": storage_gb}, ("block", "persistent")
    ))
    m.add_device(VirtualDeviceSpec(
        "nic0", "VNIC", "pci:0",
        {"links": 1}, ("network", "ethernet")
    ))
    m.add_device(VirtualDeviceSpec(
        "tpm0", "VTPM", "security:0",
        {"version": "2.0"}, ("secure_boot", "attestation")
    ))
    if gpu:
        m.add_device(VirtualDeviceSpec(
            "gpu0", "VGPU", "pci:1",
            {"count": 1}, ("accelerator", "graphics")
        ))
    return m
