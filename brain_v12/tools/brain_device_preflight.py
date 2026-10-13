#!/usr/bin/env python3
"""Safe, non-secret-leaking diagnostics for the Electronic Brain device bridge.

Read-only by default. --heartbeat sends one authenticated heartbeat; it does not
poll for tasks, consume queued work, or execute commands on the device.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_BRAIN_URL = "http://127.0.0.1:8012"
DEFAULT_AGENT_ID = "redmi3-01"
DEFAULT_KEY_FILE = "~/v12-agent/agent.key"


def request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None,
                 payload: dict | None = None, timeout: int = 12) -> tuple[int, dict | None]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(1_000_000).decode("utf-8", "replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            return response.status, parsed if isinstance(parsed, dict) else None
    except urllib.error.HTTPError as exc:
        # Do not print server bodies; they may contain implementation details.
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"NETWORK_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 0, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--heartbeat", action="store_true",
                        help="send exactly one authenticated heartbeat after preflight")
    args = parser.parse_args()

    base_url = os.getenv("V12_BRAIN_URL", DEFAULT_BRAIN_URL).strip().rstrip("/")
    agent_id = os.getenv("V12_AGENT_ID", DEFAULT_AGENT_ID).strip()
    key_path = Path(os.path.expanduser(os.getenv("V12_AGENT_KEY_FILE", DEFAULT_KEY_FILE)))
    if not base_url.startswith("https://") and not (
        base_url.startswith("http://127.0.0.1") or base_url.startswith("http://localhost")
    ):
        print("CONFIG_ERROR: remote Brain URL must use HTTPS")
        return 2
    if not agent_id or any(c in agent_id for c in "\r\n"):
        print("CONFIG_ERROR: V12_AGENT_ID is empty or invalid")
        return 2

    print(f"Brain URL: {base_url}")
    print(f"Agent ID: {agent_id}")
    print(f"Key file exists: {key_path.is_file()} (key value is never printed)")

    code, health = request_json(base_url + "/health")
    if code != 200 or not health:
        print(f"HEALTH_CHECK_FAILED: HTTP {code or 'network error'}")
        return 3
    print("Health: HTTP 200")
    print(f"Brain version: {health.get('version', 'unknown')}")
    print(f"Worker state: {(health.get('worker') or {}).get('state', 'unknown')}")

    code, status = request_json(base_url + "/api/device/status")
    if code != 200 or not status:
        print(f"DEVICE_STATUS_FAILED: HTTP {code or 'network error'}")
        return 4
    configured = status.get("configured") is True
    enabled = status.get("enabled") is True
    print(f"Device bridge configured: {configured}")
    print(f"Device bridge enabled: {enabled}")
    print(f"Auth mode: {status.get('auth_mode', 'unknown')}")
    print(f"Any agent online: {(status.get('agents') or {}).get('online', False)}")

    if not args.heartbeat:
        print("READ_ONLY_COMPLETE: no heartbeat sent; no task was polled or executed.")
        return 0 if health.get("ok") is True else 5

    if not configured or not enabled:
        print("HEARTBEAT_NOT_SENT: configure the matching agent credential on Render first.")
        return 6
    try:
        key = key_path.read_text(encoding="utf-8").strip()
    except OSError:
        print("HEARTBEAT_NOT_SENT: key file is missing or unreadable.")
        return 7
    if not key:
        print("HEARTBEAT_NOT_SENT: key file is empty.")
        return 7

    headers = {"X-V12-Agent-Key": key, "X-V12-Agent-Id": agent_id}
    code, result = request_json(
        base_url + "/api/device/heartbeat",
        method="POST",
        headers=headers,
        payload={"agent_id": agent_id, "metadata": {"agent": "BRAIN_EMULATOR_PREFLIGHT"}},
    )
    if code not in (200, 201) or not result:
        print(f"HEARTBEAT_FAILED: HTTP {code or 'network error'}; secret was not displayed.")
        return 8
    print("HEARTBEAT_ACCEPTED: one authenticated heartbeat succeeded.")
    print("NOTE: this does not prove task polling/execution; the agent loop must still run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
