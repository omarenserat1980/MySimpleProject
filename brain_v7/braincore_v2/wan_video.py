"""Client used by the Electronic Brain to submit jobs to a self-hosted Wan2.1 gateway."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

WAN_GATEWAY_URL = os.getenv("WAN_GATEWAY_URL", "").rstrip("/")
WAN_GATEWAY_TOKEN = os.getenv("WAN_GATEWAY_TOKEN", "")
WAN_GATEWAY_TIMEOUT = float(os.getenv("WAN_GATEWAY_TIMEOUT", "30"))


def generate_video(prompt: str, size: str | None = None) -> dict[str, Any]:
    if not WAN_GATEWAY_URL:
        return {"status": "PROPOSED", "reason": "WAN_GATEWAY_URL_NOT_CONFIGURED"}
    headers = {"Authorization": f"Bearer {WAN_GATEWAY_TOKEN}"} if WAN_GATEWAY_TOKEN else {}
    payload = {"prompt": prompt}
    if size:
        payload["size"] = size
    try:
        with httpx.Client(timeout=WAN_GATEWAY_TIMEOUT) as client:
            response = client.post(f"{WAN_GATEWAY_URL}/generate", json=payload, headers=headers)
            response.raise_for_status()
            return {"status": "QUEUED", **response.json()}
    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}


def wait_for_video(job_id: str, timeout: int = 3600, poll: int = 10) -> dict[str, Any]:
    if not WAN_GATEWAY_URL:
        return {"status": "FAILED", "reason": "WAN_GATEWAY_URL_NOT_CONFIGURED"}
    headers = {"Authorization": f"Bearer {WAN_GATEWAY_TOKEN}"} if WAN_GATEWAY_TOKEN else {}
    deadline = time.time() + max(1, timeout)
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=WAN_GATEWAY_TIMEOUT) as client:
                response = client.get(f"{WAN_GATEWAY_URL}/jobs/{job_id}", headers=headers)
                response.raise_for_status()
                data = response.json()
            if data.get("status") in {"SUCCEEDED", "FAILED"}:
                return data
        except Exception as exc:
            return {"status": "FAILED", "error": str(exc)}
        time.sleep(max(1, poll))
    return {"status": "TIMEOUT", "job_id": job_id}


def local_output_path(job: dict[str, Any]) -> Path | None:
    value = job.get("output")
    return Path(value) if value else None
