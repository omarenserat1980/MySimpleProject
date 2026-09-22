"""Video generation client for the Electronic Brain.

Supports RunPod Serverless or the self-hosted Wan gateway. A video is not
considered successful merely because a job was queued: callers can use
generate_and_wait() to wait for a terminal result before advancing the queue.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx

WAN_GATEWAY_URL = os.getenv("WAN_GATEWAY_URL", "").rstrip("/")
WAN_GATEWAY_TOKEN = os.getenv("WAN_GATEWAY_TOKEN", "")
WAN_GATEWAY_TIMEOUT = float(os.getenv("WAN_GATEWAY_TIMEOUT", "30"))
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "")
RUNPOD_BASE_URL = os.getenv("RUNPOD_BASE_URL", "https://api.runpod.ai/v2").rstrip("/")


def _runpod_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def generate_video(prompt: str, size: str | None = None) -> dict[str, Any]:
    """Queue a video generation job."""
    if RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID:
        payload: dict[str, Any] = {"input": {"prompt": prompt}}
        if size:
            payload["input"]["size"] = size
        try:
            with httpx.Client(timeout=WAN_GATEWAY_TIMEOUT) as client:
                response = client.post(
                    f"{RUNPOD_BASE_URL}/{RUNPOD_ENDPOINT_ID}/run",
                    json=payload,
                    headers=_runpod_headers(),
                )
                response.raise_for_status()
                data = response.json()
            return {"status": "QUEUED", "provider": "runpod", **data}
        except Exception as exc:
            return {"status": "FAILED", "provider": "runpod", "error": str(exc)}

    if not WAN_GATEWAY_URL:
        return {"status": "PROPOSED", "reason": "VIDEO_GPU_NOT_CONFIGURED"}

    headers = {"Authorization": f"Bearer {WAN_GATEWAY_TOKEN}"} if WAN_GATEWAY_TOKEN else {}
    payload = {"prompt": prompt}
    if size:
        payload["size"] = size
    try:
        with httpx.Client(timeout=WAN_GATEWAY_TIMEOUT) as client:
            response = client.post(f"{WAN_GATEWAY_URL}/generate", json=payload, headers=headers)
            response.raise_for_status()
            return {"status": "QUEUED", "provider": "wan_gateway", **response.json()}
    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}


def wait_for_video(job_id: str, timeout: int = 3600, poll: int = 10) -> dict[str, Any]:
    """Poll the selected provider until a terminal result is returned."""
    deadline = time.time() + max(1, timeout)
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=WAN_GATEWAY_TIMEOUT) as client:
                if RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID:
                    response = client.get(
                        f"{RUNPOD_BASE_URL}/{RUNPOD_ENDPOINT_ID}/status/{job_id}",
                        headers=_runpod_headers(),
                    )
                elif WAN_GATEWAY_URL:
                    headers = {"Authorization": f"Bearer {WAN_GATEWAY_TOKEN}"} if WAN_GATEWAY_TOKEN else {}
                    response = client.get(
                        f"{WAN_GATEWAY_URL}/jobs/{job_id}",
                        headers=headers,
                    )
                else:
                    return {"status": "FAILED", "reason": "VIDEO_GPU_NOT_CONFIGURED"}
                response.raise_for_status()
                data = response.json()
            if data.get("status") in {"COMPLETED", "SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT"}:
                return data
        except Exception as exc:
            return {"status": "FAILED", "error": str(exc)}
        time.sleep(max(1, poll))
    return {"status": "TIMEOUT", "job_id": job_id}


def generate_and_wait(prompt: str, size: str | None = None, timeout: int = 3600, poll: int = 10) -> dict[str, Any]:
    """Generate and wait; only a completed provider result counts as success."""
    queued = generate_video(prompt, size)
    if queued.get("status") != "QUEUED":
        return queued
    job_id = queued.get("id") or queued.get("job_id")
    if not job_id:
        return {
            "status": "FAILED",
            "provider": queued.get("provider"),
            "reason": "JOB_ID_MISSING",
            "queued": queued,
        }
    result = wait_for_video(str(job_id), timeout=timeout, poll=poll)
    return {
        "status": "COMPLETED" if result.get("status") in {"COMPLETED", "SUCCEEDED"} else result.get("status", "FAILED"),
        "provider": queued.get("provider"),
        "job_id": job_id,
        "queued": queued,
        "result": result,
    }


def local_output_path(job: dict[str, Any]) -> Path | None:
    value = job.get("output")
    if isinstance(value, str) and value:
        return Path(value)
    if isinstance(value, dict) and isinstance(value.get("path"), str):
        return Path(value["path"])
    return None
