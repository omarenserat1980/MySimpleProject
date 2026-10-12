"""Safe Brain Fabric node agent.

The agent only authenticates to the Brain control plane, reports local
capabilities, and sends periodic heartbeats. It does NOT execute arbitrary
inbound commands or shell payloads.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import signal
import time
from typing import Callable
from urllib.request import Request, urlopen


def _env_capabilities() -> list[str]:
    raw = os.getenv("BRAIN_NODE_CAPABILITIES", "python")
    return sorted(set(x.strip() for x in raw.split(",") if x.strip()))


def _memory_mb() -> int:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size / (1024 * 1024))
    except (AttributeError, OSError, ValueError):
        return 0


def _storage_gb() -> int:
    try:
        path = os.getenv("BRAIN_NODE_STORAGE_PATH", os.getcwd())
        return int(shutil.disk_usage(path).total / (1024**3))
    except OSError:
        return 0


def node_identity() -> dict:
    return {
        "node_id": os.getenv("BRAIN_NODE_ID", platform.node() or "brain-node"),
        "architecture": platform.machine() or "unknown",
        "cpu": os.cpu_count() or 1,
        "memory_mb": _memory_mb(),
        "storage_gb": _storage_gb(),
        "capabilities": _env_capabilities(),
    }


def post_json(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


def enroll(base_url: str, node_id: str, control_token: str, ttl_seconds: int = 900) -> str:
    if not control_token:
        raise ValueError("control token is required for enrollment")
    result = post_json(
        base_url.rstrip("/") + "/v1/fabric/enroll",
        {"node_id": node_id, "ttl_seconds": ttl_seconds},
        token=control_token,
    )
    token = result.get("enrollment_token")
    if not token:
        raise RuntimeError("control plane returned no enrollment token")
    return token


def heartbeat(base_url: str, enrollment_token: str) -> dict:
    base = base_url.rstrip("/")
    node = node_identity()
    return post_json(
        base + "/v1/fabric/nodes/" + node["node_id"] + "/heartbeat",
        {
            "enrollment_token": enrollment_token,
            "state": "READY",
            "jobs_running": 0,
            "architecture": node["architecture"],
            "cpu": node["cpu"],
            "memory_mb": node["memory_mb"],
            "storage_gb": node["storage_gb"],
            "capabilities": node["capabilities"],
        },
    )


def run_forever(
    base_url: str,
    enrollment_token: str,
    poll_seconds: float = 30,
    sender: Callable[[str, str], dict] = heartbeat,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    interval = max(1.0, float(poll_seconds))
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    for sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if sig is not None:
            try:
                signal.signal(sig, stop)
            except (OSError, ValueError):
                pass

    while not stopping:
        sender(base_url, enrollment_token)
        if not stopping:
            sleep(interval)


def main() -> None:
    url = os.getenv("BRAIN_NODE_URL")
    token = os.getenv("BRAIN_NODE_ENROLLMENT_TOKEN")
    if not url:
        raise SystemExit("BRAIN_NODE_URL is required")

    if not token:
        control_token = os.getenv("BRAIN_CONTROL_TOKEN")
        if not control_token:
            raise SystemExit(
                "BRAIN_NODE_ENROLLMENT_TOKEN or BRAIN_CONTROL_TOKEN is required"
            )
        token = enroll(
            url,
            node_identity()["node_id"],
            control_token,
            int(os.getenv("BRAIN_NODE_ENROLLMENT_TTL_SECONDS", "900")),
        )

    run_forever(
        url,
        token,
        float(os.getenv("BRAIN_NODE_POLL_SECONDS", "30")),
    )


if __name__ == "__main__":
    main()
