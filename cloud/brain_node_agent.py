"""Minimal Brain Node Agent.

This agent never accepts arbitrary inbound commands. It enrolls once, reports
capabilities/heartbeat, and polls only the authenticated Brain control plane.
Execution is intentionally limited to an explicit allowlist and is a later
phase.
"""
from __future__ import annotations
import json, os, platform, time
from urllib.request import Request, urlopen

def node_identity() -> dict:
    return {
        "node_id": os.getenv("BRAIN_NODE_ID", platform.node() or "brain-node"),
        "architecture": platform.machine(),
        "cpu": os.cpu_count() or 1,
        "capabilities": [x for x in os.getenv("BRAIN_NODE_CAPABILITIES", "python").split(",") if x.strip()],
    }

def post_json(url: str, payload: dict, token: str | None = None) -> dict:
    headers={"Content-Type":"application/json"}
    if token:
        headers["Authorization"]="Bearer "+token
    req=Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())

def heartbeat(base_url: str, enrollment_token: str) -> dict:
    base=base_url.rstrip("/")
    node=node_identity()
    return post_json(base+"/v1/fabric/nodes/"+node["node_id"]+"/heartbeat", {
        "enrollment_token": enrollment_token,
        "architecture": node["architecture"],
        "cpu": node["cpu"],
        "capabilities": node["capabilities"],
        "jobs_running": 0,
    })

if __name__ == "__main__":
    url=os.getenv("BRAIN_NODE_URL")
    token=os.getenv("BRAIN_NODE_ENROLLMENT_TOKEN")
    if not url or not token:
        raise SystemExit("BRAIN_NODE_URL and BRAIN_NODE_ENROLLMENT_TOKEN are required")
    print(json.dumps(heartbeat(url, token), ensure_ascii=False))
