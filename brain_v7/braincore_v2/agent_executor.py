"""Bounded bridge from the cognitive brain to the local Agent.

The brain can perform a broader set of workspace-safe terminal actions while
the Agent remains authenticated and subject to its configured command policy.
No shell=True is used.
"""
import os
from typing import Any
import httpx

from .wan_video import generate_and_wait

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
    "workspace_tree": ["find", ".", "-maxdepth", "2", "-type", "f"],
    "python_help": ["python", "-c", "print('Python execution bridge OK')"],
    "video_generate": None,
    "pytest_collect": ["pytest", "--collect-only", "-q"],
}

def execute_action(action: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or {}
    command = SAFE_ACTIONS.get(action)
    if action == "video_generate":
        prompt = str(state.get("video_prompt") or state.get("objective") or "").strip()
        if not prompt:
            return {"status": "PROPOSED", "action": action, "reason": "VIDEO_PROMPT_REQUIRED"}
        result = generate_and_wait(prompt, state.get("video_size"), timeout=int(state.get("video_timeout", 3600)), poll=int(state.get("video_poll", 10)))
        return {"status": "EXECUTED" if result.get("status") == "COMPLETED" else result.get("status", "FAILED"), "action": action, "result": result}
    if command is None:
        return {"status": "PROPOSED", "action": action, "reason": "ACTION_NOT_REGISTERED"}
    if not AGENT_TOKEN:
        return {"status": "PROPOSED", "action": action, "reason": "AGENT_TOKEN_NOT_CONFIGURED"}

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
        return {"status": "FAILED", "action": action, "command": command, "error": str(exc)}


def execute_task(actions: list[str], state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or {}
    results = []
    for index, action in enumerate(actions[:8]):
        result = execute_action(action, state)
        results.append({"step": index + 1, **result})
        if result.get("status") != "EXECUTED":
            return {"status": "FAILED", "completed_steps": index, "results": results}
    return {"status": "COMPLETED", "completed_steps": len(results), "results": results}
