"""Safe bridge from the cognitive orchestrator to the local Agent.

Only named, predefined actions are executable. Unknown actions remain proposals.
No shell strings and no shell=True are used.
"""
import os
from typing import Any
import httpx

AGENT_URL = os.getenv("AGENT_URL", "http://127.0.0.1:9000").rstrip("/")
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "")
AGENT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "35"))

SAFE_ACTIONS = {
    "python_version": ["python", "--version"],
    "git_version": ["git", "--version"],
    "git_status": ["git", "status", "--short"],
    "inspect": ["python", "-c", "print('Electronic Brain Agent inspection OK')"],
}

def execute_action(action: str, state: dict[str, Any]) -> dict[str, Any]:
    command = SAFE_ACTIONS.get(action)
    if command is None:
        return {
            "status": "PROPOSED",
            "action": action,
            "reason": "ACTION_NOT_REGISTERED",
        }

    if not AGENT_TOKEN:
        return {
            "status": "PROPOSED",
            "action": action,
            "reason": "AGENT_TOKEN_NOT_CONFIGURED",
        }

    try:
        response = httpx.post(
            f"{AGENT_URL}/execute",
            params={"token": AGENT_TOKEN},
            json={"command": command, "timeout": 30, "cwd": "."},
            timeout=AGENT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "status": "EXECUTED" if data.get("ok") else "FAILED",
            "action": action,
            "command": command,
            "result": data,
        }
    except Exception as exc:
        return {
            "status": "FAILED",
            "action": action,
            "command": command,
            "error": str(exc),
        }
