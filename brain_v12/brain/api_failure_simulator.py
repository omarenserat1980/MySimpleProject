"""Simulation-only diagnostics for Brain's local API startup path.

This module never opens sockets, starts processes, or changes a real device.
Every result is explicitly tagged SIMULATED and must not be used as proof that
the real Brain API is available.
"""
from __future__ import annotations

from typing import Any

SIMULATED = "SIMULATED"

_ACTIONS = {
    "REFUSED": (
        "API_UNREACHABLE",
        "Inspect runtime logs and dependency/import errors before considering a restart.",
    ),
    "TIMEOUT": (
        "API_TIMEOUT",
        "Check bind address, routing, and firewall in the real environment.",
    ),
    "LISTENING": (
        "API_REACHABLE",
        "Check /health and readiness, then validate authentication separately.",
    ),
    "HTTP_401": (
        "AUTH_REJECTED",
        "Compare client/server key configuration without printing or logging secrets.",
    ),
    "HTTP_403": (
        "AUTH_FORBIDDEN",
        "Inspect authorization policy and agent permissions; do not weaken the gate.",
    ),
}


def diagnose_api_state(
    *,
    port_state: str,
    process_running: bool | None = None,
    http_status: int | None = None,
) -> dict[str, Any]:
    """Return a deterministic next-step recommendation for a simulated API state.

    port_state accepts REFUSED, TIMEOUT, LISTENING, or HTTP. HTTP states require
    http_status. No network request is performed.
    """
    state = str(port_state).strip().upper()

    if state == "HTTP":
        if http_status == 401:
            key = "HTTP_401"
        elif http_status == 403:
            key = "HTTP_403"
        elif http_status is not None and 200 <= http_status < 300:
            key = "LISTENING"
        else:
            return {
                "ok": False,
                "status": "UNCLASSIFIED_HTTP_STATUS",
                "http_status": http_status,
                "reality": SIMULATED,
                "next_step": "Inspect the response and application logs; do not infer health from an unknown status.",
            }
    else:
        key = state

    if key not in _ACTIONS:
        return {
            "ok": False,
            "status": "UNSUPPORTED_SIMULATED_STATE",
            "port_state": state,
            "reality": SIMULATED,
            "next_step": "Use REFUSED, TIMEOUT, LISTENING, or HTTP with an explicit status code.",
        }

    status, next_step = _ACTIONS[key]
    if key == "REFUSED" and process_running is True:
        next_step = "A process is reported running but the port refused: inspect bind address, port, crash logs, and listener ownership."
    elif key == "REFUSED" and process_running is False:
        next_step = "The API process is reported stopped: inspect startup logs and dependencies before restarting."
    elif key == "REFUSED" and process_running is None:
        next_step = "Determine whether the API process is running, then inspect startup logs and dependencies."

    return {
        "ok": True,
        "status": status,
        "port_state": key,
        "process_running": process_running,
        "http_status": http_status,
        "reality": SIMULATED,
        "next_step": next_step,
    }
