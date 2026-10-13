"""Deterministic Linux-environment simulator for Brain.

This module models a Linux execution profile for safe planning and tests. It does
not run Linux, probe the host, allocate resources, launch QEMU, or authorize a
real Windows Server boot. Simulation results are deliberately not host evidence.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "brain.linux.simulation.v1"
SIMULATED = "SIMULATED"


def evaluate_linux_simulation(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a modeled Linux profile without touching the host or its resources.

    Expected optional profile keys: name, architecture, vcpus, memory_mib, disk_gib,
    qemu_expected, kvm_expected, uefi_expected. These are modeled inputs only.
    """
    p = dict(profile or {})
    name = str(p.get("name", "brain-linux-sandbox")).strip()
    architecture = str(p.get("architecture", "x86_64")).lower()
    try:
        vcpus = int(p.get("vcpus", 2))
        memory_mib = int(p.get("memory_mib", 4096))
        disk_gib = int(p.get("disk_gib", 32))
    except (TypeError, ValueError):
        vcpus, memory_mib, disk_gib = 0, 0, 0

    checks = {
        "profile_name": bool(name),
        "architecture_supported_by_model": architecture in {"x86_64", "amd64"},
        "positive_vcpus": vcpus >= 1,
        "positive_memory": memory_mib >= 128,
        "positive_disk": disk_gib >= 1,
        "qemu_modeled_available": p.get("qemu_expected", True) is True,
        "kvm_modeled_available": p.get("kvm_expected", True) is True,
        "uefi_modeled_available": p.get("uefi_expected", True) is True,
    }
    passed = all(checks.values())
    return {
        "schema": SCHEMA,
        "simulation_status": "SIMULATION_PASS" if passed else "SIMULATION_BLOCKED",
        "fidelity": SIMULATED,
        "profile": {
            "name": name,
            "architecture": architecture,
            "vcpus": vcpus,
            "memory_mib": memory_mib,
            "disk_gib": disk_gib,
        },
        "checks": checks,
        "blockers": [key.upper() + "_FAILED" for key, ok in checks.items() if not ok],
        "host_capacity_verified": False,
        "native_linux_running": False,
        "qemu_started": False,
        "kvm_access_verified": False,
        "resources_allocated": False,
        "external_network_enabled": False,
        "real_execution_authorized": False,
        "windows_boot_verified": False,
        "side_effects_performed": False,
        "warning": "SIMULATION_ONLY_NOT_HOST_OR_GUEST_EVIDENCE",
    }
