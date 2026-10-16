#!/usr/bin/env python3
"""Read-only audit of Brain V12 device-auth configuration.

This tool never generates, prints, hashes, sends, or replaces credentials.
It performs GET requests only and does not send a heartbeat, poll tasks, or
change service/device settings. A status endpoint cannot prove key equality.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8012"
DEFAULT_AGENT_ID = "redmi3-01"


def safe_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        return False
    if parsed.scheme == "https":
        return True
    return parsed.hostname.lower() in {"127.0.0.1", "localhost", "::1"}


def get_json(url: str, timeout: float) -> tuple[int | None, object]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(512_000).decode("utf-8", "replace")
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, {"response": "NON_JSON"}
    except urllib.error.HTTPError as exc:
        return exc.code, {"response": "HTTP_ERROR"}
    except Exception as exc:
        return None, {"response": "NETWORK_ERROR", "error_type": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("V12_BRAIN_URL", DEFAULT_URL))
    parser.add_argument("--agent-id", default=os.getenv("V12_AGENT_ID", DEFAULT_AGENT_ID))
    parser.add_argument("--key-file", default=os.getenv("V12_AGENT_KEY_FILE", "~/v12-agent/agent.key"))
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    base = args.url.strip().rstrip("/")
    key_path = Path(args.key_file).expanduser()
    print("BRAIN DEVICE AUTH AUDIT — READ ONLY")
    print(f"base_url={base}")
    print(f"agent_id={args.agent_id}")
    print(f"key_file_exists={key_path.is_file()}")
    try:
        key_present = key_path.is_file() and bool(key_path.read_text(encoding="utf-8").strip())
        print(f"local_key_nonempty={key_present}")
    except OSError as exc:
        key_present = False
        print(f"local_key_readable=false ({type(exc).__name__})")

    if not safe_url(base):
        print("STOP=INVALID_OR_INSECURE_URL")
        print("No network request was made; remote URLs must use HTTPS.")
        return 2

    health_code, health = get_json(base + "/health", args.timeout)
    print(f"health_http_status={health_code}")
    if isinstance(health, dict):
        print("health_ok=" + str(health.get("ok", "unknown")))
    status_code, status = get_json(base + "/api/device/status", args.timeout)
    print(f"device_status_http_status={status_code}")
    if status_code != 200 or not isinstance(status, dict):
        print("STOP=DEVICE_STATUS_UNAVAILABLE")
        print("No credential was sent and no setting was changed.")
        return 3

    configured = status.get("configured") is True
    enabled = status.get("enabled") is True
    auth_mode = status.get("auth_mode", "unknown")
    agents = status.get("agents") if isinstance(status.get("agents"), dict) else {}
    known_agents = agents.get("agents") if isinstance(agents.get("agents"), list) else []
    agent_record = next((x for x in known_agents if isinstance(x, dict) and x.get("agent_id") == args.agent_id), None)

    print(f"server_configured={configured}")
    print(f"server_enabled={enabled}")
    print(f"server_auth_mode={auth_mode}")
    print(f"target_agent_seen_in_status={agent_record is not None}")
    if agent_record:
        print(f"target_agent_online={agent_record.get('online') is True}")
        print(f"target_agent_state={agent_record.get('state', 'unknown')}")

    if not configured or not enabled:
        print("DECISION=STOP_CONFIGURATION_NOT_READY")
    elif not key_present:
        print("DECISION=STOP_LOCAL_KEY_MISSING_OR_EMPTY")
    else:
        print("DECISION=STOP_KEY_MATCH_NOT_PROVEN")
    print("KEY_SOURCE_PROVEN=false")
    print("KEY_MATCH_PROVEN=false")
    print("No credential was generated, displayed, hashed, or transmitted.")
    print("No heartbeat was sent, no task was created, and no settings were changed.")
    return 0 if configured and enabled and key_present else 4


if __name__ == "__main__":
    raise SystemExit(main())
