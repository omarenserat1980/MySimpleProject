"""Fail-closed, read-only transport boundary for a Brain-owned Render Cat adapter.

This module does not discover credentials, change provider settings, deploy, or
assume that a Render Cat implementation exists. It only makes bounded GET
probes when an operator has already configured BRAIN_RENDER_CAT_BASE_URL.
A successful HTTP response is transport evidence, not proof of deployment or
service identity; callers must inspect and record the returned identity.
"""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

_ALLOWED_PATHS = (
    "/health",
    "/api/deploy/identity",
    "/api/brain-hub/config",
    "/api/brain-hub/actions",
)
_MAX_RESPONSE_BYTES = 64 * 1024
_DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class ChannelResult:
    status: str
    ok: bool
    endpoint: str | None = None
    http_status: int | None = None
    data: Any = None
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ok": self.ok,
            "endpoint": self.endpoint,
            "http_status": self.http_status,
            "data": self.data,
            "detail": self.detail,
            "external_side_effects": False,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RenderCatReadOnlyChannel:
    """A read-only channel. No mutating HTTP verbs are exposed."""

    def __init__(self, base_url: str | None = None, token: str | None = None,
                 timeout: float | None = None) -> None:
        self.base_url = (base_url if base_url is not None else
                         os.getenv("BRAIN_RENDER_CAT_BASE_URL", "")).strip().rstrip("/")
        self._token = token if token is not None else os.getenv("BRAIN_RENDER_CAT_TOKEN", "")
        try:
            requested_timeout = float(timeout if timeout is not None else
                                      os.getenv("BRAIN_RENDER_CAT_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS))
        except (TypeError, ValueError):
            requested_timeout = _DEFAULT_TIMEOUT_SECONDS
        self.timeout = min(max(requested_timeout, 1.0), 10.0)

    def status(self) -> dict[str, Any]:
        parsed = urllib.parse.urlsplit(self.base_url)
        configured = bool(self.base_url)
        valid = parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password
        return {
            "channel": "render-cat-read-only",
            "configured": configured,
            "configuration_valid": valid,
            "transport": "HTTPS_GET_ONLY",
            "allowed_paths": list(_ALLOWED_PATHS),
            "connection_status": "NOT_PROBED",
            "credential_present": bool(self._token),
            "credential_value_exposed": False,
            "external_side_effects": False,
        }

    def get(self, path: str) -> dict[str, Any]:
        if path not in _ALLOWED_PATHS:
            return ChannelResult("PATH_NOT_ALLOWED", False, detail="Only approved read-only paths are allowed.").as_dict()

        parsed = urllib.parse.urlsplit(self.base_url)
        if not self.base_url:
            return ChannelResult("NOT_CONFIGURED", False, detail="BRAIN_RENDER_CAT_BASE_URL is not configured.").as_dict()
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            return ChannelResult("INVALID_CONFIGURATION", False, detail="A credential-free HTTPS base URL is required.").as_dict()
        if parsed.query or parsed.fragment:
            return ChannelResult("INVALID_CONFIGURATION", False, detail="Base URL must not contain a query or fragment.").as_dict()

        url = self.base_url + path
        headers = {"Accept": "application/json", "User-Agent": "ElectronicBrain-RenderCatReadOnly/1.0"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        request = urllib.request.Request(url, headers=headers, method="GET")
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            with opener.open(request, timeout=self.timeout) as response:
                http_status = response.status
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_RESPONSE_BYTES:
                return ChannelResult("RESPONSE_TOO_LARGE", False, path, http_status).as_dict()
            try:
                data = json.loads(raw.decode("utf-8")) if raw else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                return ChannelResult("NON_JSON_RESPONSE", False, path, http_status).as_dict()
            if not 200 <= http_status < 300:
                return ChannelResult("HTTP_ERROR", False, path, http_status, data).as_dict()
            return ChannelResult("HTTP_RESPONDED_IDENTITY_UNVERIFIED", True, path, http_status, data,
                                 "HTTP response received; service identity and live readiness remain unverified.").as_dict()
        except urllib.error.HTTPError as exc:
            return ChannelResult("HTTP_ERROR", False, path, exc.code).as_dict()
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, socket.timeout):
                detail = "Connection timed out."
            else:
                detail = "Connection failed."
            return ChannelResult("CONNECTION_FAILED", False, path, detail=detail).as_dict()
        except (TimeoutError, socket.timeout):
            return ChannelResult("CONNECTION_FAILED", False, path, detail="Connection timed out.").as_dict()
        except OSError:
            return ChannelResult("CONNECTION_FAILED", False, path, detail="Transport error.").as_dict()


def render_cat_channel_status() -> dict[str, Any]:
    """Public status entry point safe for diagnostics and UI display."""
    return RenderCatReadOnlyChannel().status()
