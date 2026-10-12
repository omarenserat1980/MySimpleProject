#!/usr/bin/env python3
"""Summarize a sanitized Electronic Brain Arkan preflight JSON report.

Read-only: parses only the supplied report and prints selected diagnostic checks.
It does not contact the network, access environment variables, or modify the report.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

KEYS = (
    "os",
    "identity",
    "hardware",
    "hyperv_module",
    "cpu_virtualization",
    "hyperv_feature",
    "hyperv_commands",
    "vms",
    "hyperv_host",
    "runner_services",
    "runner_directories",
    "disk_space",
    "candidate_vm_files",
    "git",
)


def compact(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    return text if len(text) <= 1800 else text[:1800] + "... [truncated]"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} PATH_TO_PREFLIGHT_JSON", file=sys.stderr)
        return 2

    path = Path(sys.argv[1]).expanduser()
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        print(f"ERROR: report not found: {path}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read valid JSON report ({type(exc).__name__})", file=sys.stderr)
        return 2

    print("BRAIN ARKAN PREFLIGHT SUMMARY")
    print(f"Machine: {report.get('machine', 'unknown')}")
    print(f"Generated UTC: {report.get('generated_utc', 'unknown')}")
    print(f"Checks recorded: {len(report.get('checks', {}))}")
    print("WINDOWS_BOOT_VERIFIED=false (preflight is not boot proof)")
    warnings = report.get("warnings", [])
    print(f"Warnings: {compact(warnings)}")
    checks = report.get("checks", {})
    for key in KEYS:
        if key in checks:
            print(f"\n[{key}]")
            print(compact(checks[key]))

    print("\nINTERPRETATION")
    hv_cmds = checks.get("hyperv_commands")
    identity = checks.get("identity")
    if isinstance(identity, dict) and identity.get("IsAdministrator") is False:
        print("- Current Windows PowerShell session is not elevated; Hyper-V host inspection may be denied.")
    hv_module = checks.get("hyperv_module")
    if isinstance(hv_module, list) and not hv_module:
        print("- Hyper-V PowerShell module is not discoverable in this session.")
    hv_cmds = checks.get("hyperv_commands")
    if isinstance(hv_cmds, dict) and not hv_cmds.get("GetVMHost", False):
        print("- Get-VMHost cmdlet is unavailable; inspect the Hyper-V module/feature state.")
    if any("hyperv_host" in str(w).lower() or "getvmhost" in str(w).lower() for w in warnings):
        print("- Hyper-V host query raised a classified warning; use its category and error ID above.")
    if checks.get("vms") == []:
        print("- No VMs were returned by Get-VM, or the query could not enumerate them.")
    virt = checks.get("cpu_virtualization")
    rows = virt if isinstance(virt, list) else ([virt] if isinstance(virt, dict) else [])
    if rows and all(isinstance(row, dict) for row in rows):
        if any(row.get("VirtualizationFirmwareEnabled") is False for row in rows):
            print("- CPU virtualization firmware flag is false; verify BIOS/UEFI virtualization.")
        elif any(row.get("VirtualizationFirmwareEnabled") is True for row in rows):
            print("- CPU virtualization firmware flag reports enabled.")
    print("- This report is diagnostic only; it does not prove Windows Server 2025 booted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
