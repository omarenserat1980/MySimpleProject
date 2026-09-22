"""Bounded bridge from the cognitive brain to the local Agent.

The brain may execute only registered, non-destructive terminal tasks. Tasks are
represented as argv lists; no shell=True or shell strings are accepted.
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
    "termux_pwd": ["pwd"],
    "termux_list": ["ls", "-la"],
    "python_help": ["python", "-c", "print('Python execution bridge OK')"],
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

    timeout = max(1, min(int(state.get("timeout", 30)), 60))
    try:
        response = httpx.post(
            f"{AGENT_URL}/execute",
            params={"token": AGENT_TOKEN},
            json={"command": command, "timeout": timeout, "cwd": "."},
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


def execute_task(actions: list[str], state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a bounded sequence and stop on the first failure."""
    state = state or {}
    results = []
    for index, action in enumerate(actions):
        result = execute_action(action, state)
        results.append({"step": index + 1, **result})
        if result.get("status") != "EXECUTED":
            return {
                "status": "FAILED",
                "completed_steps": index,
                "results": results,
            }
    return {
        "status": "COMPLETED",
        "completed_steps": len(results),
        "results": results,
    }
