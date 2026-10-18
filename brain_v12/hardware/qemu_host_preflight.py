"""Read-only QEMU/KVM host preflight; never starts a VM or claims guest boot."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

MAX_OUTPUT = 1200
OVMF_CANDIDATES = (
    "/usr/share/OVMF/OVMF_CODE_4M.fd",
    "/usr/share/OVMF/OVMF_CODE.fd",
    "/usr/share/edk2/ovmf/OVMF_CODE.fd",
)


def _version(binary: str) -> dict[str, Any]:
    path = shutil.which(binary)
    if not path:
        return {"available": False, "path": None, "version": None}
    try:
        proc = subprocess.run(
            [path, "--version"], capture_output=True, text=True,
            timeout=5, check=False, shell=False,
            env={"PATH": str(Path(path).parent), "LANG": "C", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "path": path, "version": None,
                "error": type(exc).__name__}
    output = (proc.stdout + proc.stderr).strip()[-MAX_OUTPUT:]
    return {"available": proc.returncode == 0, "path": path,
            "version": output or None, "return_code": proc.returncode}


def _memory_available_kib(meminfo_path: str) -> int | None:
    try:
        for line in Path(meminfo_path).read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def probe_host(
    *,
    meminfo_path: str = "/proc/meminfo",
    kvm_path: str = "/dev/kvm",
    ovmf_candidates: tuple[str, ...] = OVMF_CANDIDATES,
) -> dict[str, Any]:
    """Inspect fixed host prerequisites using bounded, read-only probes."""
    qemu = _version("qemu-system-x86_64")
    qemu_img = _version("qemu-img")
    kvm = Path(kvm_path)
    firmware = next((p for p in ovmf_candidates if Path(p).is_file()), None)
    memory_kib = _memory_available_kib(meminfo_path)
    checks = {
        "qemu_system": qemu["available"],
        "qemu_img": qemu_img["available"],
        "kvm_device": kvm.exists(),
        "ovmf_firmware": firmware is not None,
        "host_memory_readable": memory_kib is not None,
    }
    ready = all(checks.values())
    return {
        "component": "qemu-kvm-host",
        "status": "HOST_PREFLIGHT_READY" if ready else "HOST_PREFLIGHT_BLOCKED",
        "evidence_class": "HOST_CAPABILITY_PROBE",
        "checks": checks,
        "qemu_system": qemu,
        "qemu_img": qemu_img,
        "kvm_device_path": kvm_path if kvm.exists() else None,
        "ovmf_firmware_path": firmware,
        "mem_available_kib": memory_kib,
        "vm_started": False,
        "guest_boot_verified": False,
        "physical_hardware_verified": False,
    }
