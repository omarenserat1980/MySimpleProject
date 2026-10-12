#!/usr/bin/env python3
"""Fail-closed root-cause gate for Arkan Windows/Hyper-V preflight reports.

This tool only reads a sanitized JSON report and prints a prioritized diagnosis.
It never changes firmware, Windows features, Hyper-V, VM files, services, or secrets.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    return []


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} REPORT.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1]).expanduser()
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"ERROR: report not found: {path}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read report ({type(exc).__name__})", file=sys.stderr)
        return 2

    checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
    blockers: list[tuple[str, str]] = []
    identity = checks.get("identity")
    if isinstance(identity, dict) and identity.get("IsAdministrator") is False:
        blockers.append(("P1", "POWERSHELL_NOT_ELEVATED: run the diagnostic in elevated Windows PowerShell."))
    cpu_rows = rows(checks.get("cpu_virtualization"))
    if cpu_rows and any(r.get("VirtualizationFirmwareEnabled") is False for r in cpu_rows):
        blockers.append(("P0", "FIRMWARE_VIRTUALIZATION_DISABLED: enable Intel VT-x/Virtualization Technology in BIOS/UEFI, save changes, and reboot."))
    if cpu_rows and any(r.get("VMMonitorModeExtensions") is False for r in cpu_rows):
        blockers.append(("P0", "VMX_EXTENSIONS_UNAVAILABLE: verify firmware virtualization is enabled and Windows is booted on the physical host, not a restricted nested VM."))
    hv_module = checks.get("hyperv_module")
    if hv_module == []:
        blockers.append(("P1", "HYPERV_POWERSHELL_MODULE_MISSING: check Windows edition and Hyper-V feature/management tools after firmware virtualization is available."))
    feature_text = json.dumps(checks.get("hyperv_feature"), ensure_ascii=False).lower().replace(" ", "")
    if any(token in feature_text for token in ('"state":"disabled"', '"installstate":"available"', '"installstate":"removed"')):
        blockers.append(("P1", "HYPERV_FEATURE_NOT_ENABLED: inspect Windows Hyper-V feature state; do not enable it until firmware virtualization is confirmed."))
    warnings = checks.get("warnings") if isinstance(checks.get("warnings"), list) else report.get("warnings", [])
    hyperv_warning = [
        str(w) for w in warnings
        if "hyperv_host" in str(w).lower() or "getvmhost" in str(w).lower()
    ]
    if hyperv_warning:
        blockers.append(("P1", "GET_VMHOST_QUERY_FAILED: inspect the sanitized category and FullyQualifiedErrorId in report warnings; do not infer boot success."))
    if checks.get("hyperv_host") is None and not hyperv_warning:
        blockers.append(("P2", "HYPERV_HOST_UNKNOWN: the report does not establish that the host query succeeded."))
    if checks.get("vms") == []:
        blockers.append(("P2", "NO_VM_INVENTORY: no VM was returned, or enumeration returned an empty list; verify after Hyper-V host access works."))

    print("ARKAN ROOT-CAUSE GATE")
    print(f"Machine: {report.get('machine', 'unknown')}")
    print("WINDOWS_BOOT_VERIFIED=false")
    if not blockers:
        print("No deterministic blocker identified by this report; this is not a boot proof.")
        print("Next: verify six protected secrets and the dedicated Linux x64 QEMU/KVM runner before any real-boot workflow.")
        return 1

    for priority, message in sorted(blockers, key=lambda item: item[0]):
        print(f"{priority} {message}")
    if any(priority == "P0" for priority, _ in blockers):
        print("STOP: resolve P0 firmware/virtualization blockers first; do not retry Windows installation yet.")
    else:
        print("STOP: resolve host/feature access blockers and validate protected execution prerequisites before retrying.")
    print("No system settings were changed by this tool.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
