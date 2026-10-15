"""Read-only preflight for a real Brain mining node.

This module does not start mining, contact a pool, or claim remote verification.
Its output is local diagnostic evidence only; the Brain control plane must
independently authenticate a fresh heartbeat before a node can be VERIFIED.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Mapping, Any


def _memory_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def _temperature_sensor_available() -> bool:
    try:
        return any(Path("/sys/class/thermal").glob("thermal_zone*/temp"))
    except OSError:
        return False


def inspect_node(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return bounded local diagnostics without exposing environment values."""
    env = os.environ if env is None else env
    termux_root = Path("/data/data/com.termux/files/usr").is_dir()
    is_termux = bool(env.get("TERMUX_VERSION")) or termux_root
    is_linux = platform.system().lower() == "linux"
    miner_path = env.get("BRAIN_CPUMINER_BIN") or shutil.which("cpuminer")
    pool_configured = bool(env.get("BRAIN_MINING_POOL_URL"))
    worker_configured = bool(env.get("BRAIN_MINING_WORKER"))
    brain_url_configured = bool(env.get("V12_BRAIN_URL") or env.get("BRAIN_URL"))
    worker_token_configured = bool(env.get("BRAIN_WORKER_TOKEN"))
    memory_available = _memory_bytes()
    blockers: list[str] = []

    if not is_linux:
        blockers.append("UNSUPPORTED_OS_FOR_THIS_PREFLIGHT")
    if not is_termux:
        blockers.append("NOT_RUNNING_IN_TERMUX")
    if not miner_path or not Path(miner_path).is_file():
        blockers.append("TRUSTED_MINER_BINARY_NOT_FOUND")
    if not pool_configured:
        blockers.append("MINING_POOL_NOT_CONFIGURED")
    if not worker_configured:
        blockers.append("POOL_WORKER_NOT_CONFIGURED")
    if not brain_url_configured:
        blockers.append("BRAIN_CONTROL_PLANE_URL_NOT_CONFIGURED")
    if not worker_token_configured:
        blockers.append("BRAIN_WORKER_AUTH_TOKEN_NOT_CONFIGURED")
    if memory_available is None:
        blockers.append("AVAILABLE_MEMORY_UNREADABLE")
    if not _temperature_sensor_available():
        blockers.append("TEMPERATURE_SENSOR_UNAVAILABLE")

    # A local probe cannot prove physical backing, remote identity, pool shares,
    # ASIC capability, or payout. Those require independent control-plane evidence.
    return {
        "schema_version": "1.0",
        "component": "brain-digital-mining-node-preflight",
        "status": "BLOCKED" if blockers else "PREFLIGHT_READY_NOT_VERIFIED",
        "execution_mode": "READ_ONLY_PREFLIGHT",
        "node_verified": False,
        "real_mining_started": False,
        "accepted_shares_verified": False,
        "revenue_verified": False,
        "environment": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_logical_count": os.cpu_count(),
            "termux_detected": is_termux,
            "available_memory_bytes": memory_available,
            "temperature_sensor_available": _temperature_sensor_available(),
            "miner_binary_present": bool(miner_path and Path(miner_path).is_file()),
            "pool_url_configured": pool_configured,
            "pool_worker_configured": worker_configured,
            "brain_url_configured": brain_url_configured,
            "worker_auth_token_configured": worker_token_configured,
        },
        "blockers": blockers,
        "verification_required": [
            "independently authenticated worker identity",
            "fresh signed or authenticated heartbeat received by Brain",
            "measured host resources and physical/cloud backing attested",
            "pool-derived accepted-share evidence for real mining",
            "independent payout evidence before claiming revenue",
        ],
        "security_note": "Secret values, pool URL, worker name, hostname, and device identifiers are not emitted.",
    }


def main() -> int:
    result = inspect_node()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PREFLIGHT_READY_NOT_VERIFIED" else 2


if __name__ == "__main__":
    sys.exit(main())
