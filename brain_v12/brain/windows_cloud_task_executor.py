"""Brain-owned remote task adapter for a verified Windows Server 2025 Fabric node."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .windows_cloud_executor import CloudWindowsVM, WindowsCloudExecutor

WINDOWS_CAPABILITIES = [
    "windows-server-2025",
    "windows-cloud",
    "brain-task-execution",
]


class WindowsCloudTaskExecutor:
    """Submit and await a Windows task through Brain Cloud Fabric.

    No local subprocess is used here. Runtime authorization must succeed before
    a Fabric job can be created.
    """

    def __init__(
        self,
        *,
        fabric_url: str | None = None,
        control_token: str | None = None,
        http: Callable[..., dict[str, Any]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.fabric_url = (fabric_url or os.getenv("BRAIN_FABRIC_URL", "")).rstrip("/")
        self.control_token = control_token or os.getenv("BRAIN_CONTROL_TOKEN", "")
        self.http = http or self._http_json
        self.sleep = sleep

    def run(
        self,
        vm: CloudWindowsVM,
        node: dict[str, Any],
        argv: list[str],
        *,
        cwd: str | None = None,
        timeout: int | None = None,
        heartbeat_timeout: float = 120.0,
        now: float | None = None,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("WINDOWS_CLOUD_ARGV_REQUIRED")
        if not self.fabric_url:
            raise RuntimeError("BRAIN_FABRIC_URL_REQUIRED")
        if not self.control_token:
            raise RuntimeError("BRAIN_CONTROL_TOKEN_REQUIRED")

        decision = WindowsCloudExecutor().verify_runtime(
            vm, node, heartbeat_timeout=heartbeat_timeout, now=now
        )
        if not decision.get("runtime_verified"):
            raise RuntimeError(
                "WINDOWS_CLOUD_RUNTIME_NOT_VERIFIED:" + str(decision.get("reason", "UNKNOWN"))
            )

        bounded_timeout = max(1, min(int(timeout or 300), 3600))
        payload: dict[str, Any] = {"argv": argv, "timeout": bounded_timeout}
        if cwd:
            payload["cwd"] = cwd

        created = self.http(
            "POST",
            f"{self.fabric_url}/v1/fabric/jobs",
            {"kind": "windows-command", "payload": payload,
             "required_capabilities": WINDOWS_CAPABILITIES},
            self.control_token,
        )
        job = created.get("job")
        if not isinstance(job, dict) or not job.get("job_id"):
            raise RuntimeError("WINDOWS_CLOUD_JOB_CREATE_INVALID_RESPONSE")

        job_id = str(job["job_id"])
        deadline = time.monotonic() + bounded_timeout + 30
        while True:
            current_response = self.http(
                "GET",
                f"{self.fabric_url}/v1/fabric/jobs/{job_id}",
                None,
                self.control_token,
            )
            current = current_response.get("job")
            if not isinstance(current, dict):
                raise RuntimeError("WINDOWS_CLOUD_JOB_STATUS_INVALID_RESPONSE")
            state = str(current.get("state", "")).upper()
            if state in {"SUCCESS", "FAILED", "CANCELLED"}:
                return {
                    "ok": state == "SUCCESS",
                    "state": state,
                    "job_id": job_id,
                    "executor": "windows-server-2025-cloud",
                    "verified_runtime": True,
                    "evidence": current.get("evidence", []),
                }
            if time.monotonic() >= deadline:
                raise TimeoutError("WINDOWS_CLOUD_JOB_TIMEOUT")
            self.sleep(max(0.1, min(float(poll_interval), 10.0)))

    @staticmethod
    def _http_json(
        method: str, url: str, body: dict[str, Any] | None, token: str
    ) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(
                f"WINDOWS_CLOUD_FABRIC_HTTP_ERROR:{type(exc).__name__}"
            ) from exc
