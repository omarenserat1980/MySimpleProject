"""Read-only capability preflight for a Linux x86_64 Windows-boot executor."""
from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path


def inspect_capabilities(environ=None, system=None, machine=None, exists=None, which=None) -> dict:
    env = os.environ if environ is None else environ
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    exists = Path.exists if exists is None else exists
    which = shutil.which if which is None else which
    checks = []

    def add(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("linux_x64", system == "Linux" and machine.lower() in {"x86_64", "amd64"},
        "PASS" if system == "Linux" and machine.lower() in {"x86_64", "amd64"} else "LINUX_X64_REQUIRED")
    kvm_path = Path("/dev/kvm")
    kvm = bool(exists(kvm_path))
    add("kvm_device", kvm, "PASS" if kvm else "KVM_UNAVAILABLE")
    for binary in ("qemu-system-x86_64", "qemu-img", "curl"):
        available = bool(which(binary))
        add("binary:" + binary, available, "PASS" if available else "MISSING_BINARY")
    registry = bool(str(env.get("BRAIN_CLOUD_EXECUTOR_REGISTRY_URL", "")).strip())
    add("executor_registry_url", registry, "PRESENT" if registry else "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED_MISSING")

    # The real-boot workflow and contract fetcher use the BRAIN_-prefixed name.
    # Accept the legacy name as a compatibility fallback for older callers.
    contract_path = str(
        env.get("BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE", "")
        or env.get("WINDOWS_EXECUTION_CONTRACT_FILE", "")
    ).strip()
    contract = bool(contract_path)
    add("execution_contract_path", contract,
        "PRESENT" if contract else "WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED")

    missing = [item for item in checks if not item["ok"]]
    return {
        "schema_version": 1,
        "status": "READY_FOR_NEXT_GATE" if not missing else "BLOCKED",
        "ready": not missing,
        "checks": checks,
        "missing_count": len(missing),
        "next_actions": list(dict.fromkeys(item["detail"] for item in missing)),
        "windows_boot_verified": False,
        "cloud_resources_changed": False,
        "secret_values_emitted": False,
    }


if __name__ == "__main__":
    print(json.dumps(inspect_capabilities(), ensure_ascii=False, indent=2))
