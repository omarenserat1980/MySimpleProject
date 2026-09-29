from __future__ import annotations

import hashlib
import hmac
import os

from .contracts import ApiResponse


def require_scope(headers: dict[str, str], scope: str) -> ApiResponse:
    expected = os.environ.get("BRAIN_GIT_TOKEN", "")
    value = headers.get("Authorization", "")
    if not expected:
        return ApiResponse(False, error="authentication_not_configured")
    if not value.startswith("Bearer "):
        return ApiResponse(False, error="authentication_required")
    token = value[7:].strip()
    if not token or not hmac.compare_digest(
        hashlib.sha256(token.encode("utf-8")).digest(),
        hashlib.sha256(expected.encode("utf-8")).digest(),
    ):
        return ApiResponse(False, error="forbidden")
    scopes = {
        item.strip()
        for item in os.environ.get(
            "BRAIN_GIT_TOKEN_SCOPES",
            "repo:read,repo:write,workflow:read,workflow:write,pull:write",
        ).split(",")
        if item.strip()
    }
    if scope not in scopes:
        return ApiResponse(False, error="forbidden")
    return ApiResponse(True, {"scope": scope})
