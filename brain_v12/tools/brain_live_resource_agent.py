"""Collect real local resource metrics and optionally report an authenticated Brain heartbeat.

The default mode is dry-run. Sending is opt-in via --send and requires a
per-agent key. A heartbeat acknowledgment proves connectivity only; it does
not prove mining, independent hardware attestation, or revenue.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def available_memory_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def collect_resource_snapshot() -> dict[str, Any]:
    """Return measured host facts without hostnames, identifiers, or secrets."""
    disk = None
    try:
        usage = __import__("shutil").disk_usage(str(Path.home()))
        disk = {"total_bytes": usage.total, "free_bytes": usage.free}
    except OSError:
        pass
    try:
        load_average = list(os.getloadavg())
    except (AttributeError, OSError):
        load_average = None
    return {
        "schema_version": "1.0",
        "component": "brain-live-resource-agent",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_logical_count": os.cpu_count(),
        "available_memory_bytes": available_memory_bytes(),
        "disk": disk,
        "load_average_1_5_15": load_average,
        "resource_metrics_are_self_reported": True,
        "mining_started": False,
        "mining_verified": False,
        "revenue_verified": False,
    }


def _validate_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("BRAIN_URL_MUST_BE_HTTP_OR_HTTPS")
    loopback_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and parsed.hostname not in loopback_hosts:
        raise ValueError("REMOTE_BRAIN_URL_REQUIRES_HTTPS")
    if parsed.username or parsed.password:
        raise ValueError("CREDENTIALS_MUST_NOT_BE_EMBEDDED_IN_URL")
    return base_url.rstrip("/")


def send_heartbeat(base_url: str, agent_id: str, agent_key: str,
                   snapshot: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]:
    """Send one authenticated heartbeat; never retries or queues arbitrary work."""
    if not agent_id.strip() or len(agent_id) > 128:
        raise ValueError("INVALID_AGENT_ID")
    if not agent_key:
        raise ValueError("AGENT_KEY_REQUIRED")
    safe_base = _validate_base_url(base_url)
    body = json.dumps({
        "agent_id": agent_id,
        "metadata": snapshot,
    }).encode("utf-8")
    request = urllib.request.Request(
        safe_base + "/api/device/heartbeat",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-V12-Agent-Id": agent_id,
            "X-V12-Agent-Key": agent_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"BRAIN_HEARTBEAT_HTTP_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"BRAIN_HEARTBEAT_FAILED:{type(exc).__name__}") from None
    acknowledged = (
        isinstance(payload, dict)
        and payload.get("ok") is True
        and payload.get("status") == "HEARTBEAT"
        and payload.get("agent_id") == agent_id
    )
    return {
        "heartbeat_acknowledged": acknowledged,
        "agent_id": agent_id,
        "brain_response_status": payload.get("status") if isinstance(payload, dict) else None,
        "resource_verified": False,
        "mining_verified": False,
        "revenue_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true",
                        help="send one authenticated heartbeat; otherwise print a local dry-run")
    args = parser.parse_args(argv)
    snapshot = collect_resource_snapshot()
    result: dict[str, Any] = {"mode": "SEND_REQUESTED" if args.send else "DRY_RUN",
                              "snapshot": snapshot}
    if args.send:
        base_url = os.getenv("V12_BRAIN_URL", "http://127.0.0.1:8012")
        agent_id = os.getenv("V12_AGENT_ID", "brain-resource-node-01")
        agent_key = os.getenv("V12_AGENT_KEY", "")
        try:
            result["delivery"] = send_heartbeat(base_url, agent_id, agent_key, snapshot)
        except (ValueError, RuntimeError) as exc:
            result["delivery"] = {"heartbeat_acknowledged": False, "error": str(exc)}
            print(json.dumps(result, sort_keys=True))
            return 3
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
