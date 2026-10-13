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
        raise RuntimeError("WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY")

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
