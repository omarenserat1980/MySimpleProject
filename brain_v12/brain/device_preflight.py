"""Read-only, privacy-conscious preflight for Brain fleet devices.

This module collects coarse runtime capability facts only. It performs no
network requests, does not inspect environment variables or credentials, and
does not authenticate the machine. A user-supplied alias is a label, not proof
of device identity. The report digest detects accidental changes only; it is
not a signature or attestation.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_ALIASES = {"arkan", "redmi", "realme", "unknown"}
TOOL_CANDIDATES = {
    "git": ("git",),
    "curl": ("curl",),
    "node": ("node", "node.exe"),
    "ffmpeg": ("ffmpeg", "ffmpeg.exe"),
    "ffprobe": ("ffprobe", "ffprobe.exe"),
    "powershell": ("pwsh", "powershell", "powershell.exe"),
    "termux_info": ("termux-info",),
}


def _memory_bytes() -> int | None:
    """Return total physical memory when the OS exposes it without extra deps."""
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except (AttributeError, OSError, TypeError, ValueError):
            return None
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return int(pages * page_size)
    except (AttributeError, OSError, ValueError):
        pass
    return None


def _tool_presence() -> dict[str, bool]:
    result: dict[str, bool] = {}
    for label, candidates in TOOL_CANDIDATES.items():
        result[label] = any(shutil.which(name) for name in candidates)
    return result


def build_preflight_report(alias: str = "unknown", cwd: str | Path | None = None) -> dict[str, Any]:
    """Build a local-only capability snapshot; no network or secret access."""
    normalized_alias = str(alias).strip().lower()
    if normalized_alias not in ALLOWED_ALIASES:
        raise ValueError(f"alias must be one of: {', '.join(sorted(ALLOWED_ALIASES))}")

    root = Path(cwd or Path.cwd()).resolve()
    try:
        disk = shutil.disk_usage(root)
        disk_report: dict[str, int | None] = {
            "total_bytes": int(disk.total),
            "free_bytes": int(disk.free),
        }
    except OSError:
        disk_report = {"total_bytes": None, "free_bytes": None}

    report: dict[str, Any] = {
        "schema_version": 1,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "device_alias": normalized_alias,
        "identity_verified": False,
        "attestation_verified": False,
        "execution_eligible": False,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        },
        "resources": {
            "logical_cpu_count": os.cpu_count(),
            "total_memory_bytes": _memory_bytes(),
            "working_volume": disk_report,
        },
        "tools": _tool_presence(),
        "network_probed": False,
        "secrets_read": False,
        "limitations": [
            "Local self-reported diagnostics only; not remote connectivity proof.",
            "Alias is user-supplied and does not establish unique device identity.",
            "Digest is an integrity checksum, not a signature or attestation.",
            "No software, service, cloud resource, or device setting was changed.",
        ],
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Create a read-only Brain device preflight JSON report.")
    parser.add_argument("--alias", choices=sorted(ALLOWED_ALIASES), default="unknown")
    parser.add_argument("--output", help="Optional path for the JSON report; stdout is used by default.")
    args = parser.parse_args(argv)
    report = build_preflight_report(alias=args.alias)
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
