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
    Invalid profile shapes and resource types fail closed.
    """
    profile_is_mapping = profile is None or isinstance(profile, dict)
    p = profile.copy() if isinstance(profile, dict) else {}

    raw_name = p.get("name", "brain-linux-sandbox")
    name_is_valid = isinstance(raw_name, str) and bool(raw_name.strip())
    name = raw_name.strip() if isinstance(raw_name, str) else ""

    raw_architecture = p.get("architecture", "x86_64")
    architecture_is_valid = isinstance(raw_architecture, str)
    architecture = raw_architecture.lower() if architecture_is_valid else ""

    def strict_int(key: str, default: int) -> int:
        value = p.get(key, default)
        # bool is a subclass of int, and floats/strings must not be silently coerced.
        return value if type(value) is int else 0

    vcpus = strict_int("vcpus", 2)
    memory_mib = strict_int("memory_mib", 4096)
    disk_gib = strict_int("disk_gib", 32)

    checks = {
        "profile_is_mapping": profile_is_mapping,
        "profile_name": name_is_valid,
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
