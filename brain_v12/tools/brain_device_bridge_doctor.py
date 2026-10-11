#!/usr/bin/env python3
"""Read-only doctor for the Brain V12 device bridge.

Checks the local Termux agent contract and the live Brain API without sending
credentials or creating tasks. The raw agent key is never printed or uploaded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://electronic-brain-v12-gwwg.onrender.com"
DEFAULT_AGENT_ID = "redmi3-01"


def get_json(url: str, timeout: float) -> tuple[int | None, object | str]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(1_000_000).decode("utf-8", "replace")
            try:
                return response.status, json.loads(raw)
            except json.JSONDecodeError:
                return response.status, raw[:2000]
    except urllib.error.HTTPError as exc:
        raw = exc.read(4000).decode("utf-8", "replace")
        try:
            body: object = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return exc.code, body
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("V12_BRAIN_URL", DEFAULT_URL))
    parser.add_argument("--agent-id", default=os.getenv("V12_AGENT_ID", DEFAULT_AGENT_ID))
    parser.add_argument("--key-file", default=os.getenv("V12_AGENT_KEY_FILE", "~/v12-agent/agent.key"))
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--show-key-sha256", action="store_true",
                        help="print the key's SHA-256 digest for configuring BRAIN_AGENT_KEY_SHA256; never prints the raw key")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    key_path = Path(args.key_file).expanduser()

    print("BRAIN DEVICE BRIDGE DOCTOR (read-only; no tasks are enqueued)")
    print(f"base_url={base}")
    print(f"agent_id={args.agent_id}")
    print(f"key_file={key_path}")
    if key_path.is_file():
        try:
            key = key_path.read_text(encoding="utf-8").strip()
            if key:
                print("local_key=FOUND_NONEMPTY")
                if args.show_key_sha256:
                    print("BRAIN_AGENT_KEY_SHA256=" + hashlib.sha256(key.encode()).hexdigest())
                else:
                    print("local_key_sha256=HIDDEN (use --show-key-sha256 only when needed)")
            else:
                print("local_key=EMPTY")
        except OSError as exc:
            print(f"local_key=UNREADABLE ({type(exc).__name__})")
    else:
        print("local_key=MISSING")

    for route in ("/health", "/api/device/status"):
        status, payload = get_json(base + route, args.timeout)
        print(f"\n[{route}] http_status={status}")
        if isinstance(payload, dict):
            # Intentionally show only non-secret diagnostic fields.
            if route == "/health":
                safe = {k: payload.get(k) for k in ("ok", "status", "brain", "version", "runtime", "state", "deployment") if k in payload}
                print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
            else:
                safe = {k: payload.get(k) for k in (
                    "ok", "enabled", "configured", "auth_env", "auth_mode",
                    "queued", "pending", "completed", "failed", "last_agent_seen", "agents"
                ) if k in payload}
                print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
                if payload.get("configured") is False:
                    print("DIAGNOSIS=server bridge has no usable credential configuration")
                if payload.get("online") is False or (isinstance(payload.get("agents"), dict) and not payload["agents"].get("online")):
                    print("DIAGNOSIS=no recent authenticated agent heartbeat is visible")
        else:
            print(str(payload)[:2000])

    print("\nNo credentials were transmitted; no task was created; no server settings were changed.")
    print("If server configured=false, configure BRAIN_AGENT_KEY_SHA256 in the Render service using the local_key_sha256 above; never paste the raw key into chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
