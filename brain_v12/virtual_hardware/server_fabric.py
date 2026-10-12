"""Simulation-first server profiles, backend discovery, and host resource admission.

This module is intentionally side-effect free: it does not create VMs, start
services, download media, or modify host configuration. All virtual capacities
are kept distinct from observed host capacity.
"""
from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


SIMULATED = "SIMULATED"
ESTIMATED = "ESTIMATED"
HOST_OBSERVED = "HOST_OBSERVED"
GUEST_VERIFIED = "GUEST_VERIFIED"
PHYSICALLY_CALIBRATED = "PHYSICALLY_CALIBRATED"


@dataclass(frozen=True)
class ServerProfile:
    profile_id: str
    label: str
    workload: str
    vcpus: int
    memory_mib: int
    disk_gib: int
    execution_mode: str = "SIMULATED_WORKFLOW"
    fidelity: str = SIMULATED
    external_network_default: bool = False

    def validate(self) -> dict[str, Any]:
        errors = []
        if not self.profile_id.strip():
            errors.append("PROFILE_ID_REQUIRED")
        if self.vcpus < 1:
            errors.append("VCPU_COUNT_MUST_BE_POSITIVE")
        if self.memory_mib < 128:
            errors.append("MEMORY_MIB_BELOW_MINIMUM")
        if self.disk_gib < 1:
            errors.append("DISK_GIB_MUST_BE_POSITIVE")
        if self.execution_mode not in {
            "SIMULATED_WORKFLOW", "VIRTUAL_SERVICE", "SANDBOXED_NATIVE",
            "VIRTUAL_MACHINE", "HARDWARE_ADAPTER",
        }:
            errors.append("UNSUPPORTED_EXECUTION_MODE")
        if self.external_network_default:
            errors.append("EXTERNAL_NETWORK_MUST_DEFAULT_TO_DISABLED")
        return {"ok": not errors, "errors": errors, "fidelity": self.fidelity}

    def describe(self) -> dict[str, Any]:
        return {**asdict(self), "validation": self.validate(),
                "capacity_semantics": "VIRTUAL_CONFIGURATION_NOT_HOST_CAPACITY"}


SERVER_PROFILES: tuple[ServerProfile, ...] = (
    # Arkan is a logical identity only: these capacities are simulated configuration,
    # not physical RAM/CPU and not a promise that this host can execute the workload.
    ServerProfile("brain-arkan-software-node-v1", "Arkan high-capacity software node", "general-purpose-compute", 128, 1024 * 1024, 100 * 1024, execution_mode="SIMULATED_WORKFLOW", fidelity=SIMULATED),
    ServerProfile("brain-server-small-v1", "Small virtual server", "general", 1, 512, 8),
    ServerProfile("brain-server-web-v1", "Web server workflow", "web", 1, 512, 8),
    ServerProfile("brain-server-database-v1", "Database workflow", "database", 2, 1024, 16),
    ServerProfile("brain-server-file-v1", "File service workflow", "file-storage", 1, 512, 16),
    ServerProfile("brain-server-api-v1", "API service workflow", "api", 1, 512, 8),
    ServerProfile("brain-server-monitoring-v1", "Monitoring workflow", "monitoring", 1, 256, 4),
    ServerProfile("brain-server-backup-v1", "Backup and recovery workflow", "backup", 1, 256, 8),
    ServerProfile("brain-server-dns-v1", "DNS test workflow", "dns", 1, 256, 4),
    ServerProfile("brain-server-dhcp-v1", "DHCP test workflow", "dhcp", 1, 256, 4),
    ServerProfile("brain-server-directory-v1", "Directory service test workflow", "directory", 2, 1024, 16),
    ServerProfile("brain-server-certificate-v1", "Certificate service test workflow", "certificate", 1, 512, 8),
    ServerProfile("brain-server-reverse-proxy-v1", "Reverse proxy workflow", "reverse-proxy", 1, 256, 4),
)


def list_server_profiles() -> list[dict[str, Any]]:
    """Return deterministic profile descriptions; no host resources are allocated."""
    return [profile.describe() for profile in SERVER_PROFILES]


def get_server_profile(profile_id: str) -> ServerProfile:
    for profile in SERVER_PROFILES:
        if profile.profile_id == profile_id:
            return profile
    raise ValueError("UNKNOWN_SERVER_PROFILE")


def validate_server_release(product: str, version: str) -> dict[str, Any]:
    """Validate known target identifiers without claiming media/license verification."""
    normalized_product = product.strip().casefold()
    normalized_version = version.strip()
    if normalized_product not in {"windows server", "windows_server"}:
        return {"ok": False, "status": "UNSUPPORTED_SERVER_PRODUCT"}
    if normalized_version == "2023":
        return {"ok": False, "status": "UNVERIFIED_WINDOWS_SERVER_RELEASE",
                "reason": "Verify the actual Microsoft product release before configuring a guest."}
    if normalized_version == "2025":
        return {"ok": True, "status": "TARGET_IDENTIFIER_RECOGNIZED",
                "product": "Windows Server", "version": "2025",
                "media_verified": False, "boot_verified": False}
    return {"ok": False, "status": "UNSUPPORTED_OR_UNVERIFIED_SERVER_RELEASE"}


@dataclass(frozen=True)
class HostCapacity:
    logical_cpus: int
    available_memory_mib: int | None
    available_disk_bytes: int | None
    operating_system: str
    architecture: str
    provenance: str = "UNVERIFIED"

    def describe(self) -> dict[str, Any]:
        return asdict(self)


def _read_int(path: str) -> int | None:
    try:
        value = Path(path).read_text(encoding="ascii").strip()
        if value and value != "max":
            return int(value)
    except (OSError, ValueError):
        pass
    return None


def _cgroup_memory_available_mib() -> int | None:
    """Return effective cgroup headroom when the host exposes a memory limit."""
    # cgroup v2
    limit = _read_int("/sys/fs/cgroup/memory.max")
    current = _read_int("/sys/fs/cgroup/memory.current")
    if limit is not None and current is not None and limit > 0:
        return max(0, limit - current) // (1024 * 1024)
    # cgroup v1
    limit = _read_int("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    current = _read_int("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    if limit is not None and current is not None and 0 < limit < (1 << 60):
        return max(0, limit - current) // (1024 * 1024)
    return None


def _available_memory_mib() -> int | None:
    """Observe memory headroom, respecting tighter cgroup limits where visible."""
    observed: int | None = None
    # Linux/Android (including Termux) path; no third-party dependency.
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                observed = max(0, int(line.split()[1]) // 1024)
                break
    except (OSError, ValueError, IndexError):
        pass
    # Windows fallback using the native memory-status API.
    if observed is None and os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                observed = int(status.ullAvailPhys // (1024 * 1024))
        except (AttributeError, OSError, TypeError):
            pass
    cgroup_available = _cgroup_memory_available_mib()
    if observed is None:
        return cgroup_available
    return min(observed, cgroup_available) if cgroup_available is not None else observed


def _effective_logical_cpus() -> int:
    """Respect CPU affinity and cgroup quota rather than host-wide CPU count alone."""
    host_count = os.cpu_count() or 1
    affinity_count = host_count
    try:
        affinity_count = max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    quota_count: int | None = None
    # cgroup v2 cpu.max contains '<quota> <period>' or 'max <period>'.
    try:
        quota_text = Path("/sys/fs/cgroup/cpu.max").read_text(encoding="ascii").split()
        if len(quota_text) == 2 and quota_text[0] != "max":
            quota, period = int(quota_text[0]), int(quota_text[1])
            if quota > 0 and period > 0:
                quota_count = max(1, (quota + period - 1) // period)
    except (OSError, ValueError, IndexError):
        pass
    # cgroup v1 CPU quota.
    if quota_count is None:
        quota = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
        period = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
        if quota is not None and period is not None and quota > 0 and period > 0:
            quota_count = max(1, (quota + period - 1) // period)
    return max(1, min(host_count, affinity_count, quota_count) if quota_count is not None
               else min(host_count, affinity_count))


def observe_host_capacity(path: str | os.PathLike[str] = ".") -> HostCapacity:
    """Observe basic host capacity without reserving resources or starting a VM."""
    logical_cpus = _effective_logical_cpus()
    available_memory_mib = _available_memory_mib()
    try:
        available_disk_bytes = shutil.disk_usage(path).free
    except OSError:
        available_disk_bytes = None
    return HostCapacity(
        logical_cpus=logical_cpus,
        available_memory_mib=available_memory_mib,
        available_disk_bytes=available_disk_bytes,
        operating_system=platform.system() or "unknown",
        architecture=platform.machine() or "unknown",
        provenance=HOST_OBSERVED,
    )


def discover_backends() -> dict[str, Any]:
    """Report backend availability; detection never starts or configures a backend."""
    system = platform.system().casefold()
    qemu = shutil.which("qemu-system-x86_64")
    qemu_aarch64 = shutil.which("qemu-system-aarch64")
    docker = shutil.which("docker")
    podman = shutil.which("podman")
    virsh = shutil.which("virsh")
    kvm_device = Path("/dev/kvm").exists() if system == "linux" else False
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    hyperv_host = system == "windows" and powershell is not None
    return {
        "host": {"operating_system": platform.system(), "architecture": platform.machine()},
        "backends": [
            {"id": "brain-simulator", "available": True, "mode": SIMULATED,
             "reason": "Internal deterministic model; not native guest execution."},
            {"id": "qemu-x86_64", "available": qemu is not None, "binary": qemu,
             "mode": "VIRTUAL_MACHINE"},
            {"id": "qemu-aarch64", "available": qemu_aarch64 is not None, "binary": qemu_aarch64,
             "mode": "VIRTUAL_MACHINE"},
            {"id": "kvm", "available": kvm_device, "device": "/dev/kvm" if kvm_device else None,
             "mode": "VIRTUAL_MACHINE", "requires": "Compatible Linux host and permissions"},
            {"id": "hyper-v", "available": hyperv_host, "powershell": powershell,
             "mode": "VIRTUAL_MACHINE", "requires": "Compatible Windows host and Hyper-V feature"},
            {"id": "libvirt", "available": virsh is not None, "binary": virsh,
             "mode": "VIRTUAL_MACHINE"},
            {"id": "docker", "available": docker is not None, "binary": docker,
             "mode": "VIRTUAL_SERVICE"},
            {"id": "podman", "available": podman is not None, "binary": podman,
             "mode": "VIRTUAL_SERVICE"},
        ],
        "provisioning_performed": False,
        "external_network_enabled": False,
    }


def admit_server_workload(
    profile: ServerProfile,
    host: HostCapacity,
    *,
    memory_reserve_mib: int = 256,
    disk_reserve_bytes: int = 1024 * 1024 * 1024,
    max_cpu_fraction: float = 0.75,
) -> dict[str, Any]:
    """Fail-closed capacity check; estimates do not allocate resources."""
    if not profile.validate()["ok"]:
        return {"ok": False, "status": "INVALID_SERVER_PROFILE",
                "validation": profile.validate()}
    if memory_reserve_mib < 0 or disk_reserve_bytes < 0:
        return {"ok": False, "status": "INVALID_RESOURCE_RESERVE"}
    if not 0 < max_cpu_fraction <= 1:
        return {"ok": False, "status": "INVALID_CPU_BUDGET"}
    if host.provenance != HOST_OBSERVED:
        return {"ok": False, "status": "HOST_CAPACITY_NOT_OBSERVED"}
    if host.logical_cpus < 1 or (host.available_memory_mib is not None and host.available_memory_mib < 0) or (host.available_disk_bytes is not None and host.available_disk_bytes < 0):
        return {"ok": False, "status": "HOST_CAPACITY_INVALID"}
    if host.available_memory_mib is None or host.available_disk_bytes is None:
        return {"ok": False, "status": "HOST_CAPACITY_UNKNOWN"}
    max_vcpus = max(1, int(host.logical_cpus * max_cpu_fraction))
    required_disk = profile.disk_gib * 1024 * 1024 * 1024
    checks = {
        "cpu": {"required_vcpus": profile.vcpus, "budget_vcpus": max_vcpus,
                "ok": profile.vcpus <= max_vcpus},
        "memory": {"required_mib": profile.memory_mib,
                   "available_mib": host.available_memory_mib,
                   "reserve_mib": memory_reserve_mib,
                   "ok": profile.memory_mib <= max(0, host.available_memory_mib - memory_reserve_mib)},
        "disk": {"required_bytes": required_disk,
                 "available_bytes": host.available_disk_bytes,
                 "reserve_bytes": disk_reserve_bytes,
                 "ok": required_disk <= max(0, host.available_disk_bytes - disk_reserve_bytes)},
    }
    ok = all(check["ok"] for check in checks.values())
    return {"ok": ok, "status": "ADMITTED_FOR_PLANNING" if ok else "INSUFFICIENT_HOST_CAPACITY",
            "profile_id": profile.profile_id, "host_provenance": host.provenance,
            "checks": checks, "resources_reserved": False, "vm_started": False,
            "external_network_enabled": False}
