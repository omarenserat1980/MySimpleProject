#!/usr/bin/env python3
"""Read-only local Android/Termux resource measurement for Brain Phone Base.

Writes local JSON evidence only. It never registers/activates a node, contacts a
pool, mines, or sends measurements over the network.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_meminfo(path: Path = Path("/proc/meminfo")) -> dict[str, int]:
    result: dict[str, int] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                result[parts[0].rstrip(":")] = int(parts[1]) * 1024
    except (OSError, ValueError):
        pass
    return result


def _android_property(name: str) -> str | None:
    getprop = shutil.which("getprop")
    if not getprop:
        return None
    try:
        completed = subprocess.run(
            [getprop, name], capture_output=True, text=True, timeout=2, check=False
        )
        value = completed.stdout.strip()
        return value or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def collect_measurement() -> dict[str, Any]:
    """Collect read-only host values; no unique hardware identifiers are queried."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    mem = _read_meminfo()
    try:
        disk = shutil.disk_usage(Path.home())
        disk_data: dict[str, int] | None = {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        }
    except OSError:
        disk_data = None

    android_release = _android_property("ro.build.version.release")
    android_sdk = _android_property("ro.build.version.sdk")
    is_termux = Path("/data/data/com.termux/files/usr").exists()
    is_android = android_release is not None or is_termux

    measurements: dict[str, Any] = {
        "cpu_logical_count": os.cpu_count(),
        "memory_bytes": {
            "total": mem.get("MemTotal"),
            "available": mem.get("MemAvailable"),
            "free": mem.get("MemFree"),
        },
        "home_filesystem_bytes": disk_data,
        "android": {
            "detected": is_android,
            "termux_detected": is_termux,
            "release": android_release,
            "sdk": android_sdk,
        },
        "runtime": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
    }
    sources = {
        "cpu_logical_count": "Python os.cpu_count() on the local host",
        "memory_bytes": "/proc/meminfo on the local host",
        "home_filesystem_bytes": "shutil.disk_usage(home directory) on the local host",
        "android": "Android getprop and Termux path presence, when available",
        "runtime": "Python platform/runtime metadata on the local host",
    }
    return {
        "schema": "brain-phone-base.real-measurement.v1",
        "measurement_id": f"local-{now}",
        "measured_at_utc": now,
        "collection_mode": "read_only_local",
        "measurements": measurements,
        "measurement_sources": sources,
        "evidence": {
            "classification": "local_measurement_unattested",
            "locally_recorded": True,
            "integrity_signature": None,
            "independent_verification": "not_performed",
            "device_identity_verified": False,
        },
        "node_gate": {
            "state": "untrusted_inactive",
            "trusted": False,
            "active": False,
            "manual_approval": "not_granted",
            "activation_allowed": False,
            "reasons": [
                "Local measurements are not independent attestation.",
                "Device identity has not been independently verified.",
                "Manual approval has not been granted.",
            ],
        },
        "network_actions": {
            "measurement_uploaded": False,
            "node_registered": False,
            "mining_started": False,
            "mining_pool_contacted": False,
        },
    }


def write_evidence(output: Path) -> dict[str, Any]:
    evidence = collect_measurement()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture read-only local phone resource evidence.")
    parser.add_argument(
        "--output",
        default="evidence/phone-real-measurement.json",
        help="Local JSON output path (default: evidence/phone-real-measurement.json)",
    )
    args = parser.parse_args()
    output = Path(args.output).expanduser()
    evidence = write_evidence(output)
    print(json.dumps({
        "output": str(output.resolve()),
        "schema": evidence["schema"],
        "classification": evidence["evidence"]["classification"],
        "node_state": evidence["node_gate"]["state"],
        "trusted": evidence["node_gate"]["trusted"],
        "active": evidence["node_gate"]["active"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
