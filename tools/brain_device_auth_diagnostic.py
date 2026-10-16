#!/usr/bin/env python3
"""Read-only Brain device-bridge authentication preflight.

Never prints secret values, never sends credentials, never polls for work,
and never changes service or device configuration.
"""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DEFAULT_URL = "https://electronic-brain-v12-gwwg.onrender.com"
BASE_URL = os.getenv("V12_BRAIN_URL", DEFAULT_URL).rstrip("/")
KEY_FILE = Path(os.path.expanduser(os.getenv(
    "V12_AGENT_KEY_FILE", "~/v12-agent/agent.key"
)))
ENV_NAMES = (
    "V12_BRAIN_URL",
    "V12_AGENT_ID",
    "V12_AGENT_KEY_FILE",
    "BRAIN_EMULATOR_KEY",
    "BRAIN_EMULATOR_KEY_FILE",
    "X_V12_AGENT_KEY",
)

def get_json(path):
    req = Request(BASE_URL + path, headers={"Accept": "application/json"},
                  method="GET")
    try:
        with urlopen(req, timeout=8) as response:
            body = response.read(65536).decode("utf-8", "replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"non_json_response": True}
            return {"http_status": response.status, "body": data}
    except HTTPError as exc:
        return {"http_status": exc.code, "error": "HTTP_ERROR"}
    except (URLError, TimeoutError, OSError) as exc:
        return {"error": type(exc).__name__}

def main():
    present = {name: bool(os.getenv(name, "").strip()) for name in ENV_NAMES}
    file_exists = KEY_FILE.is_file()
    file_nonempty = False
    if file_exists:
        try:
            file_nonempty = KEY_FILE.stat().st_size > 0
        except OSError:
            pass

    health = get_json("/health")
    liveness = get_json("/api/brain/liveness")
    bridge = {}
    body = liveness.get("body", {})
    if isinstance(body, dict):
        checks = body.get("checks", {})
        if isinstance(checks, dict):
            bridge = checks.get("device_bridge", {}) or {}

    report = {
        "mode": "READ_ONLY_NO_CREDENTIALS_SENT",
        "base_url": BASE_URL,
        "environment_variable_presence_only": present,
        "local_key_file": {
            "path": str(KEY_FILE),
            "exists": file_exists,
            "nonempty": file_nonempty,
            "value_read_or_printed": False,
        },
        "health_http": health,
        "liveness_http": liveness,
        "device_bridge_status": {
            "configured": bridge.get("configured"),
            "agents_online": bridge.get("agents_online"),
            "agent_count": len(bridge.get("agents", {}).get("agents", []))
                if isinstance(bridge.get("agents"), dict) else None,
        },
        "authentication_proof": "NOT_TESTED",
        "reason": (
            "This diagnostic intentionally does not send secrets or call poll/execute. "
            "A successful authenticated no-op endpoint is required to prove authentication."
        ),
        "tasks_executed": False,
        "settings_changed": False,
        "secrets_created": False,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
