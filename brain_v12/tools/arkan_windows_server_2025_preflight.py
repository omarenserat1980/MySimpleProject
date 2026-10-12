"""Fail-closed readiness gate for a real Windows Server 2025 guest on Arkan.

This module does not provision resources, download media, create disks, or start a VM.
It distinguishes the canonical software identity from the real QEMU/KVM substrate
required to execute a Windows kernel.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from pathlib import Path
from typing import Any

ARKAN_ID = "arkan-virtual-01"
MIN_CPU_CORES = 2
MIN_TOTAL_MEMORY_MIB = 4096
MIN_AVAILABLE_MEMORY_MIB = 3072
MIN_FREE_DISK_GIB = 25
REQUIRED_TOOLS = ("qemu-system-x86_64", "qemu-img", "xorriso", "wimlib-imagex", "mcopy")
OVMF_CANDIDATES = (
    "/usr/share/OVMF/OVMF_CODE_4M.fd",
    "/usr/share/OVMF/OVMF_CODE.fd",
    "/usr/share/edk2/ovmf/OVMF_CODE_4M.fd",
    "/usr/share/edk2/ovmf/OVMF_CODE.fd",
)


def read_memory_mib(path: str | Path = "/proc/meminfo") -> tuple[int, int]:
    """Return total and available memory in MiB; fail closed if unavailable."""
    values: dict[str, int] = {}
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable"}:
                values[key] = int(raw.strip().split()[0]) // 1024
    except (OSError, ValueError, IndexError):
        return 0, 0
    return values.get("MemTotal", 0), values.get("MemAvailable", 0)


def evaluate_readiness(facts: dict[str, Any]) -> dict[str, Any]:
    """Evaluate host facts without making changes or claiming Windows is booted."""
    checks: dict[str, bool] = {
        "canonical_arkan_identity": facts.get("canonical_id") == ARKAN_ID,
        "linux_host": facts.get("os") == "Linux",
        "x86_64_host": str(facts.get("arch", "")).lower() in {"x86_64", "amd64"},
        "cpu_capacity": int(facts.get("cpu_cores") or 0) >= MIN_CPU_CORES,
        "total_memory": int(facts.get("total_memory_mib") or 0) >= MIN_TOTAL_MEMORY_MIB,
        "available_memory": int(facts.get("available_memory_mib") or 0) >= MIN_AVAILABLE_MEMORY_MIB,
        "free_disk": int(facts.get("free_disk_gib") or 0) >= MIN_FREE_DISK_GIB,
        "kvm_device": facts.get("kvm_read_write") is True,
        "qemu": facts.get("tools", {}).get("qemu-system-x86_64") is True,
        "qemu_img": facts.get("tools", {}).get("qemu-img") is True,
        "media_tools": all(facts.get("tools", {}).get(n) is True for n in ("xorriso", "wimlib-imagex", "mcopy")),
        "uefi_firmware": facts.get("ovmf_readable") is True,
        "signed_contract_gate": facts.get("contract_verified") is True,
    }
    blockers = [name.upper() + "_NOT_READY" for name, passed in checks.items() if not passed]
    ready = not blockers
    return {
        "schema": "brain.arkan.windows-server-2025-readiness.v1",
        "arkan_id": ARKAN_ID,
        "status": "READY_FOR_AUTHORIZED_REAL_BOOT" if ready else "BLOCKED",
        "ready": ready,
        "checks": checks,
        "blockers": blockers,
        "execution_backend": "qemu-kvm",
        "os_target": "Windows Server 2025 x64",
        "installation_status": "NOT_STARTED",
        "boot_status": "NOT_VERIFIED",
        "windows_boot_verified": False,
        "side_effects_performed": False,
        "capacity_is_simulated": False,
    }


def inspect_host(workspace: str | Path = ".",
                 contract_gate_path: str | Path = "windows-execution-contract-gate.json") -> dict[str, Any]:
    total_mib, available_mib = read_memory_mib()
    try:
        free_bytes = shutil.disk_usage(Path(workspace).resolve()).free
    except OSError:
        free_bytes = 0
    kvm = Path("/dev/kvm")
    ovmf = next((p for p in OVMF_CANDIDATES if Path(p).is_file() and os.access(p, os.R_OK)), None)
    tools = {name: shutil.which(name) is not None for name in REQUIRED_TOOLS}
    for alternative in ("mkfs.vfat", "mkfs.fat"):
        if shutil.which(alternative):
            tools["fat_mkfs"] = True
            break
    else:
        tools["fat_mkfs"] = False

    contract_verified = False
    try:
        gate = json.loads(Path(contract_gate_path).read_text(encoding="utf-8"))
        contract_verified = gate.get("verified") is True
    except (OSError, json.JSONDecodeError):
        pass

    facts = {
        "canonical_id": os.environ.get("BRAIN_ARKAN_ID", ARKAN_ID),
        "os": platform.system(),
        "arch": platform.machine(),
        "cpu_cores": os.cpu_count() or 0,
        "total_memory_mib": total_mib,
        "available_memory_mib": available_mib,
        "free_disk_gib": free_bytes // (1024 ** 3),
        "kvm_read_write": kvm.exists() and os.access(kvm, os.R_OK | os.W_OK),
        "tools": tools,
        "ovmf_readable": bool(ovmf),
        "contract_verified": contract_verified,
    }
    result = evaluate_readiness(facts)
    result["observed"] = {
        "host_os": facts["os"],
        "host_arch": facts["arch"],
        "cpu_cores": facts["cpu_cores"],
        "total_memory_mib": total_mib,
        "available_memory_mib": available_mib,
        "free_disk_gib": facts["free_disk_gib"],
        "ovmf_path": ovmf,
        "tool_availability": tools,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--contract-gate", default="windows-execution-contract-gate.json")
    parser.add_argument("--output", default="arkan-windows-server-2025-readiness.json")
    args = parser.parse_args()
    result = inspect_host(args.workspace, args.contract_gate)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
