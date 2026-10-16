#!/usr/bin/env python3
"""Read-only inventory of likely local mining runtimes; never launches or configures miners.

The doctor reports observable names only. It deliberately does not capture process
command lines, environment variables, registry values other than installed-app display
names, credentials, pool settings, or wallet addresses.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from typing import Any

MINER_PATTERNS = (
    "cgminer", "bfgminer", "cpuminer", "minerd", "xmrig", "nicehash",
    "nbminer", "t-rex", "trex", "lolminer", "teamredminer", "phoenixminer",
    "gminer", "bzminer", "wildrig", "braiins", "bosminer", "asicminer",
)
MINER_BINARIES = (
    "cgminer", "bfgminer", "cpuminer", "minerd", "xmrig", "nbminer",
    "t-rex", "lolminer", "teamredminer", "phoenixminer", "gminer", "bzminer",
    "bosminer",
)


def _matches(values: list[str]) -> list[str]:
    result: dict[str, str] = {}
    for value in values:
        name = str(value).strip()
        if name and any(pattern in name.casefold() for pattern in MINER_PATTERNS):
            result.setdefault(name.casefold(), name[:160])
    return sorted(result.values(), key=str.casefold)


def _run_readonly(command: list[str], timeout: int = 12) -> tuple[int, str]:
    """Run a fixed inventory command; callers must never pass user-supplied commands."""
    try:
        # Keep only runtime paths needed by fixed read-only commands. In particular,
        # PowerShell needs PSModulePath to auto-load built-in cmdlets such as ConvertTo-Json.
        safe_env_keys = ("PATH", "SystemRoot", "WINDIR", "PSModulePath", "TEMP", "TMP")
        safe_env = {key: os.environ.get(key, "") for key in safe_env_keys}
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False,
            shell=False, env=safe_env,
        )
        return completed.returncode, completed.stdout[:200_000]
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def _find_powershell() -> str | None:
    """Find PowerShell even when a managed Python process has a reduced PATH."""
    shell = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
    if shell:
        return shell

    # Some Windows launchers omit System32 from PATH. Use the well-known Windows PowerShell
    # location as a fallback, but only if the executable exists. Do not invoke a shell lookup.
    root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if root:
        candidates = (
            os.path.join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"),
            os.path.join(root, "Sysnative", "WindowsPowerShell", "v1.0", "powershell.exe"),
        )
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
    return None


def _windows_inventory() -> tuple[dict[str, list[str]], dict[str, bool]]:
    # Fixed PowerShell script: read-only process/service/task/app inventory. No command lines,
    # environment values, service paths, registry keys, or configuration values are returned.
    script = r'''
$ErrorActionPreference = 'SilentlyContinue'
$processes = @(Get-Process | ForEach-Object { $_.ProcessName })
$services = @(Get-Service | ForEach-Object { $_.Name; $_.DisplayName })
$tasks = @(Get-ScheduledTask | ForEach-Object { $_.TaskName; $_.TaskPath })
$apps = @()
$paths = @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*')
foreach ($path in $paths) { $apps += @(Get-ItemProperty -Path $path | ForEach-Object { $_.DisplayName }) }
[pscustomobject]@{processes=$processes;services=$services;tasks=$tasks;apps=$apps} | ConvertTo-Json -Compress -Depth 3
'''
    shell = _find_powershell()
    if not shell:
        return {"processes": [], "services": [], "tasks": [], "apps": []}, {
            "processes": False, "services": False, "tasks": False, "apps": False,
        }
    # Windows inventory can take longer on hosts with many scheduled tasks.
    code, output = _run_readonly([shell, "-NoProfile", "-NonInteractive", "-Command", script], timeout=30)
    if code != 0 or not output.strip():
        return {"processes": [], "services": [], "tasks": [], "apps": []}, {
            "processes": False, "services": False, "tasks": False, "apps": False,
        }
    try:
        data = json.loads(output)
        if not isinstance(data, dict):
            raise ValueError("unexpected PowerShell inventory shape")
        categories = {}
        for key in ("processes", "services", "tasks", "apps"):
            value = data.get(key, [])
            categories[key] = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        return categories, {"processes": True, "services": True, "tasks": True, "apps": True}
    except (json.JSONDecodeError, ValueError):
        return {"processes": [], "services": [], "tasks": [], "apps": []}, {
            "processes": False, "services": False, "tasks": False, "apps": False,
        }


def collect_diagnostics(system: str | None = None) -> dict[str, Any]:
    """Collect read-only process/PATH and, on Windows, service/task/app-name evidence."""
    system = (system or platform.system()).casefold()
    evidence: dict[str, list[str]] = {
        "process_candidates": [], "service_candidates": [],
        "scheduled_task_candidates": [], "installed_app_candidates": [],
        "miner_binaries_on_path": [],
    }
    availability = {"processes": False, "services": False, "scheduled_tasks": False, "installed_apps": False, "path_binaries": True}

    for binary in MINER_BINARIES:
        if shutil.which(binary):
            evidence["miner_binaries_on_path"].append(binary)

    if system == "windows":
        inventory, available = _windows_inventory()
        evidence["process_candidates"] = _matches(inventory["processes"])
        evidence["service_candidates"] = _matches(inventory["services"])
        evidence["scheduled_task_candidates"] = _matches(inventory["tasks"])
        evidence["installed_app_candidates"] = _matches(inventory["apps"])
        availability = {
            "processes": available["processes"], "services": available["services"],
            "scheduled_tasks": available["tasks"], "installed_apps": available["apps"],
            "path_binaries": True,
        }
    elif system in {"linux", "darwin"}:
        command = ["ps", "-eo", "comm="] if system == "linux" else ["ps", "-axo", "comm="]
        code, output = _run_readonly(command)
        availability["processes"] = code == 0
        evidence["process_candidates"] = _matches(output.splitlines()) if code == 0 else []
    else:
        availability["processes"] = False

    found = any(evidence.values())
    scanned = any(availability[key] for key in ("processes", "services", "scheduled_tasks", "installed_apps"))
    status = "MINER_CANDIDATE_DETECTED" if found else "NO_KNOWN_MINER_DETECTED" if scanned else "INSUFFICIENT_DIAGNOSTIC_CAPABILITY"
    return {
        "schema_version": 1,
        "status": status,
        "read_only": True,
        "settings_changed": False,
        "miner_started_or_stopped": False,
        "network_scan_performed": False,
        "secrets_read": False,
        "system": system,
        "evidence_sources_available": availability,
        "evidence": evidence,
        "limitations": [
            "Name-based matching can miss vendor-specific or renamed miners.",
            "An external ASIC or remote/vendor-managed worker may not appear in this host inventory.",
            "No candidate found is not proof that no miner exists.",
            "This report does not verify pool connectivity, accepted shares, hashrate, payout, or revenue.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    report = collect_diagnostics()
    if args.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print(f"Mining runtime doctor: {report['status']}")
        print("Read-only: yes; settings changed: no; miner started/stopped: no")
        for category, names in report["evidence"].items():
            if names:
                print(f"{category}: {', '.join(names)}")
        for limitation in report["limitations"]:
            print(f"Limitation: {limitation}")
    return 0 if report["status"] != "INSUFFICIENT_DIAGNOSTIC_CAPABILITY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
