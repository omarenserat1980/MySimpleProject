"""Fail-closed, read-only Render API client.

Live requests are disabled by default. Tests should inject a fake transport.
No mutation methods or arbitrary URL support are exposed.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable
from urllib.parse import urlencode

_API_BASE = "https://api.render.com/v1"
_SERVICE_ID = re.compile(r"^srv-[A-Za-z0-9]+$")
_SECRET_KEYS = re.compile(r"(token|secret|password|api[_-]?key|authorization)", re.I)
_BEARER = re.compile(r"(?i)\bBearer\s+[^\s,;]+")
_KEY_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|authorization)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)


class RenderConnectorError(RuntimeError):
    """A safe-to-display connector error."""


def redact(value: Any) -> Any:
    """Recursively redact credential-like fields and common log formats."""
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _SECRET_KEYS.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _KEY_VALUE.sub(r"\1\2[REDACTED]", _BEARER.sub("Bearer [REDACTED]", value))
    return value


def _default_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, str]:
    """Perform one HTTPS GET without following redirects."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
            return None

    request = urllib.request.Request(url, headers=headers, method="GET")
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # Keep response bodies bounded and redact before returning.
        body = exc.read(64_000).decode("utf-8", errors="replace")
        return exc.code, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RenderConnectorError("Render request failed; details withheld for safety.") from exc


class RenderReadOnlyClient:
    """Small allowlisted Render API client; disabled unless explicitly enabled."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        api_key: str | None = None,
        timeout: float = 5.0,
        transport: Callable[[str, dict[str, str], float], tuple[int, str]] | None = None,
    ) -> None:
        if not 0 < timeout <= 15:
            raise ValueError("timeout must be greater than 0 and at most 15 seconds")
        self.enabled = enabled
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport or _default_transport

    @classmethod
    def from_environment(cls, *, enabled: bool = False, timeout: float = 5.0) -> "RenderReadOnlyClient":
        # Reads an existing credential only when the caller explicitly enables the client.
        key = os.environ.get("RENDER_API_KEY") if enabled else None
        return cls(enabled=enabled, api_key=key, timeout=timeout)

    def service(self, service_id: str) -> Any:
        return self._get(f"/services/{self._validate_service_id(service_id)}")

    def deploys(self, service_id: str, *, limit: int = 10) -> Any:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        path = f"/services/{self._validate_service_id(service_id)}/deploys"
        return self._get(path, {"limit": limit})

    def logs(
        self,
        resource_id: str,
        *,
        start_time: str,
        end_time: str,
        limit: int = 100,
    ) -> Any:
        # Render log API uses a resource selector and bounded time window.
        if not _SERVICE_ID.fullmatch(resource_id):
            raise ValueError("invalid Render resource id")
        if not start_time or not end_time or len(start_time) > 40 or len(end_time) > 40:
            raise ValueError("start_time and end_time are required and must be bounded")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        return self._get("/logs", {
            "resource": resource_id,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit,
        })

    @staticmethod
    def _validate_service_id(service_id: str) -> str:
        if not isinstance(service_id, str) or not _SERVICE_ID.fullmatch(service_id):
            raise ValueError("invalid Render service id")
        return service_id

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.enabled:
            raise RenderConnectorError("Render connector is disabled; no network request was made.")
        if not self._api_key:
            raise RenderConnectorError("Render API credential is not configured.")
        # Paths are constructed internally from allowlisted read-only methods.
        url = _API_BASE + path
        if params:
            url += "?" + urlencode(params)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
            "User-Agent": "Electronic-Brain-V12-Render-ReadOnly/1.0",
        }
        status, body = self._transport(url, headers, self._timeout)
        if status < 200 or status >= 300:
            raise RenderConnectorError(f"Render returned HTTP {status}: {self._safe_body(body)}")
        try:
            return redact(json.loads(body))
        except (json.JSONDecodeError, TypeError) as exc:
            raise RenderConnectorError("Render returned an invalid JSON response.") from exc

    @staticmethod
    def _safe_body(body: str) -> str:
        try:
            value = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            value = body[:2000]
        return json.dumps(redact(value), ensure_ascii=False)[:2000]
