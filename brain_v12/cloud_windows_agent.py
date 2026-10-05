from __future__ import annotations

"""Windows Cloud node registration/heartbeat helper.

Runs inside a real Windows Server 2025 cloud VM. It never provisions
infrastructure and never stores provider credentials. The VM must be
enrolled with Brain Cloud Fabric and then reports its capability/heartbeat.
"""

import os
import platform
import time
import urllib.request
import json


def _post(url: str, payload: dict, token: str) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode())


def heartbeat() -> dict:
    origin = os.getenv("BRAIN_FABRIC_URL", "").rstrip("/")
    node_id = os.getenv("BRAIN_WINDOWS_NODE_ID", platform.node()).strip()
    token = os.getenv("BRAIN_ENROLLMENT_TOKEN", "").strip()
    if not origin or not node_id or not token:
        return {
            "ok": False,
            "status": "NOT_CONFIGURED",
            "reason": "BRAIN_FABRIC_URL_NODE_ID_OR_ENROLLMENT_TOKEN_MISSING",
        }

    payload = {
        "enrollment_token": token,
        "state": "READY",
        "jobs_running": 0,
        "architecture": "x86_64" if platform.machine().lower() in {"amd64", "x86_64"} else platform.machine(),
        "capabilities": [
            "windows-server-2025",
            "windows-cloud",
            "brain-task-execution",
            "brain-heartbeat",
            "brain-evidence",
        ],
    }
    result = _post(f"{origin}/v1/fabric/nodes/{node_id}/heartbeat", payload, token)
    return {"ok": True, "status": "HEARTBEAT_SENT", "node": result.get("node")}


if __name__ == "__main__":
    result = heartbeat()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result.get("ok") else 2)
