from __future__ import annotations

"""Discover and verify Brain Fabric Windows Cloud nodes.

This module is deliberately read-only: it never provisions infrastructure.
A node becomes usable only after a fresh Fabric heartbeat and the
Windows Cloud verification gate both pass.
"""

import time
from typing import Any

from .windows_cloud_gate import verify_windows_cloud_node


def discover_windows_cloud_nodes(
    nodes: list[dict[str, Any]],
    *,
    heartbeat_timeout: float = 120.0,
    now: float | None = None,
) -> dict[str, Any]:
    current = time.time() if now is None else float(now)
    verified: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for node in nodes:
        result = verify_windows_cloud_node(node)
        heartbeat = float(node.get("last_heartbeat", 0) or 0)
        fresh = heartbeat > 0 and current - heartbeat <= heartbeat_timeout
        if result["verified"] and fresh:
            verified.append({**result, "heartbeat_fresh": True})
        else:
            rejected.append({
                "node_id": node.get("node_id"),
                "verified": False,
                "reason": "WINDOWS_CLOUD_HEARTBEAT_STALE" if result["verified"] and not fresh else result.get("reason"),
            })

    return {
        "status": "WINDOWS_CLOUD_AVAILABLE" if verified else "WINDOWS_CLOUD_UNAVAILABLE",
        "verified": bool(verified),
        "nodes": verified,
        "rejected": rejected,
        "heartbeat_timeout_seconds": heartbeat_timeout,
    }
