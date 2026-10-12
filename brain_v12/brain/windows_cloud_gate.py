from __future__ import annotations

"""Fail-closed gate for a real Windows Server 2025 cloud node."""

import time
from typing import Any

WINDOWS_CLOUD = "windows-server-2025-cloud"


def verify_windows_cloud_node(
    node: dict[str, Any],
    *,
    heartbeat_timeout: float | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    required = {
        "node_id": node.get("node_id"),
        "provider": node.get("provider"),
        "state": node.get("state"),
        "architecture": str(node.get("architecture", "")).lower(),
        "last_heartbeat": node.get("last_heartbeat"),
    }
    missing = [k for k, v in required.items() if v in (None, "", 0)]
    capabilities = {str(x).strip() for x in node.get("capabilities", [])}
    required_caps = {"windows-server-2025", "windows-cloud", "brain-heartbeat"}
    missing_caps = sorted(required_caps - capabilities)

    if missing or missing_caps:
        return {
            "verified": False,
            "status": "WINDOWS_CLOUD_NOT_VERIFIED",
            "reason": "WINDOWS_CLOUD_NODE_EVIDENCE_INCOMPLETE",
            "missing": missing,
            "missing_capabilities": missing_caps,
        }

    if required["architecture"] not in {"x86_64", "amd64"}:
        return {
            "verified": False,
            "status": "WINDOWS_CLOUD_NOT_VERIFIED",
            "reason": "WINDOWS_CLOUD_ARCHITECTURE_INVALID",
        }

    if str(required["state"]).upper() not in {"READY", "RUNNING"}:
        return {
            "verified": False,
            "status": "WINDOWS_CLOUD_NOT_VERIFIED",
            "reason": "WINDOWS_CLOUD_NODE_NOT_READY",
        }

    result = {
        "verified": True,
        "status": "WINDOWS_CLOUD_VERIFIED",
        "executor": WINDOWS_CLOUD,
        "node_id": required["node_id"],
        "provider": required["provider"],
        "architecture": required["architecture"],
        "capabilities": sorted(capabilities),
    }

    if heartbeat_timeout is not None:
        current = time.time() if now is None else float(now)
        heartbeat = float(required["last_heartbeat"] or 0)
        fresh = heartbeat > 0 and current - heartbeat <= heartbeat_timeout
        if not fresh:
            return {
                **result,
                "verified": False,
                "status": "WINDOWS_CLOUD_NOT_VERIFIED",
                "reason": "WINDOWS_CLOUD_HEARTBEAT_STALE",
                "heartbeat_timeout_seconds": heartbeat_timeout,
            }
        result["heartbeat_fresh"] = True

    return result
