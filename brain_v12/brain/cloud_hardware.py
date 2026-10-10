"""Provider-neutral Brain Cloud MAX hardware and capability fabric.

P0: virtual motherboard + normalized executor capability model.
The model deliberately separates declared, observed, and provider-owned
properties so Brain never mistakes a target architecture for real hardware.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


class CapabilityError(ValueError):
    """Raised when a hardware manifest is structurally invalid."""


@dataclass(frozen=True)
class CPU:
    architecture: str
    sockets: int
    cores: int
    threads: int
    numa_nodes: int = 1
    features: tuple[str, ...] = ()


@dataclass(frozen=True)
class Memory:
    bytes: int
    ecc: bool = True
    numa_nodes: int = 1


@dataclass(frozen=True)
class GPU:
    model: str
    count: int
    vram_bytes: int
    interconnect: str = "none"


@dataclass(frozen=True)
class Storage:
    fast_bytes: int
    object_bytes: int = 0
    archive_bytes: int = 0
    nvme_devices: int = 0


@dataclass(frozen=True)
class Network:
    bandwidth_bps: int
    rdma: bool = False
    interfaces: int = 1


@dataclass(frozen=True)
class Firmware:
    uefi: bool = True
    secure_boot: bool = False
    vtpm: bool = False
    boot_order: tuple[str, ...] = ("nvme", "network")


@dataclass(frozen=True)
class Management:
    virtual_bmc: bool = True
    power_telemetry: bool = False
    thermal_telemetry: bool = False


@dataclass(frozen=True)
class Availability:
    zones: int = 1
    snapshots: bool = False
    cross_region: bool = False


@dataclass
class HardwareManifest:
    machine_id: str
    executor_class: str
    state: str
    source: str
    cpu: CPU
    memory: Memory
    gpu: GPU
    storage: Storage
    network: Network
    firmware: Firmware
    management: Management
    availability: Availability
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.machine_id.strip():
            raise CapabilityError("machine_id is required")
        if self.executor_class not in {"cpu", "gpu", "storage", "recovery", "control"}:
            raise CapabilityError("invalid executor_class")
        if self.state not in {"online", "offline", "quarantined", "draining"}:
            raise CapabilityError("invalid state")
        if self.source not in {"declared", "observed", "provider_owned", "mixed"}:
            raise CapabilityError("invalid source")
        if self.cpu.sockets < 1 or self.cpu.cores < 1 or self.cpu.threads < self.cpu.cores:
            raise CapabilityError("invalid CPU topology")
        if self.cpu.numa_nodes < 1 or self.memory.bytes < 0 or self.gpu.count < 0:
            raise CapabilityError("invalid compute resources")
        if self.gpu.count == 0 and self.gpu.vram_bytes != 0:
            raise CapabilityError("GPU VRAM cannot exist without a GPU")
        if self.gpu.count > 0 and self.gpu.vram_bytes <= 0:
            raise CapabilityError("GPU VRAM is required when GPUs exist")
        if min(self.storage.fast_bytes, self.storage.object_bytes, self.storage.archive_bytes) < 0:
            raise CapabilityError("storage capacities cannot be negative")
        if self.network.bandwidth_bps < 0 or self.network.interfaces < 1:
            raise CapabilityError("invalid network capacity")
        if self.availability.zones < 1:
            raise CapabilityError("availability must contain at least one zone")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @property
    def total_vram_bytes(self) -> int:
        return self.gpu.vram_bytes

    @property
    def logical_threads(self) -> int:
        return self.cpu.threads


@dataclass(frozen=True)
class WorkloadRequirement:
    cpu_threads: int = 0
    memory_bytes: int = 0
    gpu_count: int = 0
    gpu_vram_bytes: int = 0
    fast_storage_bytes: int = 0
    network_bps: int = 0
    rdma: bool = False
    kvm: bool = False
    secure_boot: bool = False
    vtpm: bool = False
    min_zones: int = 1

    def validate(self) -> None:
        values = (
            self.cpu_threads, self.memory_bytes, self.gpu_count,
            self.gpu_vram_bytes, self.fast_storage_bytes, self.network_bps,
        )
        if any(v < 0 for v in values) or self.min_zones < 1:
            raise CapabilityError("requirements cannot be negative")


def satisfies(manifest: HardwareManifest, req: WorkloadRequirement) -> bool:
    manifest.validate()
    req.validate()
    return (
        manifest.state == "online"
        and manifest.logical_threads >= req.cpu_threads
        and manifest.memory.bytes >= req.memory_bytes
        and manifest.gpu.count >= req.gpu_count
        and manifest.total_vram_bytes >= req.gpu_vram_bytes
        and manifest.storage.fast_bytes >= req.fast_storage_bytes
        and manifest.network.bandwidth_bps >= req.network_bps
        and (not req.rdma or manifest.network.rdma)
        and (not req.kvm or manifest.metadata.get("kvm", False))
        and (not req.secure_boot or manifest.firmware.secure_boot)
        and (not req.vtpm or manifest.firmware.vtpm)
        and manifest.availability.zones >= req.min_zones
    )


def score(manifest: HardwareManifest, req: WorkloadRequirement) -> tuple[int, int, int, str]:
    """Deterministic best-fit score: avoid wasting scarce GPU/RAM resources."""
    if not satisfies(manifest, req):
        return (-1, -1, -1, manifest.machine_id)
    excess_gpu = manifest.gpu.count - req.gpu_count
    excess_ram = manifest.memory.bytes - req.memory_bytes
    excess_cpu = manifest.logical_threads - req.cpu_threads
    return (-excess_gpu, -excess_ram, -excess_cpu, manifest.machine_id)


def select_executor(
    manifests: Iterable[HardwareManifest], req: WorkloadRequirement
) -> HardwareManifest | None:
    candidates = [m for m in manifests if satisfies(m, req)]
    return max(candidates, key=lambda m: score(m, req), default=None)


def build_virtual_motherboard(machine_id: str = "brain-cloud-max-01") -> HardwareManifest:
    """Reference P0 target; it is a declaration, not a claim of provisioned hardware."""
    return HardwareManifest(
        machine_id=machine_id,
        executor_class="gpu",
        state="offline",
        source="declared",
        cpu=CPU("x86_64", sockets=2, cores=384, threads=768, numa_nodes=8),
        memory=Memory(bytes=6 * 1024**4, ecc=True, numa_nodes=8),
        gpu=GPU("target-gpu-class", count=8, vram_bytes=8 * 192 * 1024**3, interconnect="fabric"),
        storage=Storage(fast_bytes=100 * 1024**4, object_bytes=1024**5, archive_bytes=10 * 1024**5, nvme_devices=16),
        network=Network(bandwidth_bps=400_000_000_000, rdma=True, interfaces=4),
        firmware=Firmware(uefi=True, secure_boot=True, vtpm=True),
        management=Management(virtual_bmc=True, power_telemetry=True, thermal_telemetry=True),
        availability=Availability(zones=3, snapshots=True, cross_region=True),
        metadata={"kvm": True, "qemu": True, "profile": "BRAIN_CLOUD_MAX_REFERENCE"},
    )
