#!/usr/bin/env python3
"""Safe diagnostics that turn recurring Windows cloud-boot blockers into actions.

Checks capability and environment-variable presence only. Never prints secret
values, calls cloud APIs, creates resources, or claims Windows booted.
"""
from __future__ import annotations
import argparse, json, os, platform, shutil
from pathlib import Path
from typing import Any

REGISTRY_ENV = (
    "BRAIN_CLOUD_EXECUTOR_REGISTRY_URL",
    "BRAIN_CLOUD_EXECUTOR_REGISTRY_TOKEN",
    "BRAIN_CLOUD_EXECUTOR_ATTESTATION_KEY",
    "BRAIN_CLOUD_EXECUTOR_AUTHORITY_PUBLIC_KEY",
    "BRAIN_WINDOWS_CONTROL_PLANE_URL",
    "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY",
)
AZURE_ENV = (
    "CHECK_AZURE_CLIENT_ID", "CHECK_AZURE_TENANT_ID",
    "CHECK_AZURE_SUBSCRIPTION_ID", "CHECK_WINDOWS_ADMIN_USERNAME",
    "CHECK_WINDOWS_ADMIN_PASSWORD",
)
REQUIRED_TOOLS = ("qemu-system-x86_64", "qemu-img", "xorriso", "wimlib-imagex", "mkfs.vfat", "mcopy")

def _check_env(names: tuple[str, ...], prefix: str) -> dict[str, Any]:
    missing = [name for name in names if not os.environ.get(name, "").strip()]
    return {"ok": not missing, "required_count": len(names),
            "present_count": len(names) - len(missing), "missing_names": missing,
            "finding": prefix + ("_READY" if not missing else "_MISSING")}

def diagnose() -> dict[str, Any]:
    arch = platform.machine().lower()
    x64 = arch in {"x86_64", "amd64"}
    kvm = Path("/dev/kvm")
    kvm_ok = kvm.exists() and os.access(kvm, os.R_OK | os.W_OK)
    tools = {name: shutil.which(name) is not None for name in REQUIRED_TOOLS}
    missing_tools = [name for name, found in tools.items() if not found]
    identity_ok = os.environ.get("BRAIN_CLOUD_EXECUTOR") == "1" and bool(os.environ.get("BRAIN_CLOUD_EXECUTOR_ID", "").strip())
    checks = {
        "architecture": {"ok": x64, "value": arch, "finding": "X64_READY" if x64 else "X64_REQUIRED"},
        "kvm_device": {"ok": kvm_ok, "value": str(kvm), "finding": "KVM_DEVICE_READY" if kvm_ok else "KVM_DEVICE_MISSING_OR_INACCESSIBLE"},
        "qemu_toolchain": {"ok": not missing_tools, "required": list(REQUIRED_TOOLS), "missing": missing_tools, "finding": "QEMU_TOOLCHAIN_READY" if not missing_tools else "QEMU_TOOLCHAIN_INCOMPLETE"},
        "executor_identity": {"ok": identity_ok, "finding": "EXECUTOR_IDENTITY_READY" if identity_ok else "EXECUTOR_IDENTITY_MISSING"},
        "registry_and_control_plane": _check_env(REGISTRY_ENV, "REGISTRY_CONTROL_PLANE"),
        "azure_and_guest_credentials": _check_env(AZURE_ENV, "AZURE_GUEST_CONFIG"),
    }
    actions = {
        "architecture": "Run on a Linux x86_64 executor; a Windows runner or ARM phone is not a substitute.",
        "kvm_device": "Provision or enable a Linux host exposing writable /dev/kvm; QEMU installation alone is insufficient.",
        "qemu_toolchain": "Install the listed QEMU, UEFI, and media utilities, then rerun this diagnostic.",
        "executor_identity": "Set executor identity only after the runner is provisioned and attestation is configured.",
        "registry_and_control_plane": "Configure missing GitHub Environment secrets by name; never place values in logs or repository files.",
        "azure_and_guest_credentials": "Configure missing Azure/guest secrets in the protected environment; validate presence without printing values.",
    }
    blockers = [{"check": key, "finding": str(value.get("finding", "BLOCKED")), "next_action": actions[key]}
                for key, value in checks.items() if value.get("ok") is not True]
    return {"schema": "brain.blocker-diagnostic.v1",
            "status": "READY_FOR_BOOT_GATE" if not blockers else "BLOCKED",
            "windows_boot_verified": False,
            "summary": {"checks": len(checks), "passed": len(checks)-len(blockers), "blockers": len(blockers)},
            "checks": checks, "blockers": blockers,
            "next_step": "Run the existing cloud executor gate and Windows completion gate; this diagnostic is not boot evidence."}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional JSON evidence file path")
    args = parser.parse_args()
    result = diagnose()
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "READY_FOR_BOOT_GATE" else 2

if __name__ == "__main__":
    raise SystemExit(main())
