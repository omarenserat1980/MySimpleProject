"""Brain Cloud Bootstrap controller.

Provider-neutral, secret-safe orchestration for the Brain Cloud edge.
It never invents credentials and never reports deployment success without
an explicit verification result.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class CloudConfig:
    cloudflare_token_configured: bool
    cloudflare_account_configured: bool
    brain_origin: str
    brain_origin_valid: bool
    pages_origin_configured: bool

    @classmethod
    def from_env(cls) -> "CloudConfig":
        origin = os.getenv("BRAIN_ORIGIN", "").strip().rstrip("/")
        return cls(
            cloudflare_token_configured=bool(os.getenv("CLOUDFLARE_API_TOKEN")),
            cloudflare_account_configured=bool(os.getenv("CLOUDFLARE_ACCOUNT_ID")),
            brain_origin=origin,
            brain_origin_valid=_https_url(origin),
            pages_origin_configured=bool(os.getenv("BRAIN_API_ORIGIN", "").strip()),
        )


def _https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def preflight() -> dict[str, Any]:
    cfg = CloudConfig.from_env()
    missing = []
    if not cfg.cloudflare_token_configured:
        missing.append("CLOUDFLARE_API_TOKEN")
    if not cfg.cloudflare_account_configured:
        missing.append("CLOUDFLARE_ACCOUNT_ID")
    if not cfg.brain_origin:
        missing.append("BRAIN_ORIGIN")
    elif not cfg.brain_origin_valid:
        return {
            "ok": False,
            "state": "BLOCKED_CONFIGURATION",
            "reason": "BRAIN_ORIGIN_MUST_BE_HTTPS",
            "missing": [],
        }

    return {
        "ok": not missing,
        "state": "READY" if not missing else "WAITING_CREDENTIALS",
        "missing": missing,
        "origin_configured": bool(cfg.brain_origin),
        "pages_origin_configured": cfg.pages_origin_configured,
    }


def verify_runtime(origin: str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    target = (origin or CloudConfig.from_env().brain_origin).rstrip("/")
    if not _https_url(target):
        return {
            "ok": False,
            "state": "BLOCKED_CONFIGURATION",
            "reason": "HTTPS_ORIGIN_REQUIRED",
        }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.get(target + "/health")
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        verified = (
            response.status_code == 200
            and payload.get("ok") is True
            and payload.get("state") == "RUNNING"
        )
        return {
            "ok": verified,
            "state": "VERIFIED_RUNNING" if verified else "RUNTIME_NOT_VERIFIED",
            "http_status": response.status_code,
            "runtime_ok": payload.get("ok"),
            "runtime_state": payload.get("state"),
        }
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "state": "RUNTIME_UNREACHABLE",
            "error": str(exc)[:500],
        }


def bootstrap_status() -> dict[str, Any]:
    """Return a safe state machine snapshot; no deployment is implied."""
    pf = preflight()
    if not pf["ok"]:
        return {"ok": False, "phase": "PREFLIGHT", "preflight": pf}
    verification = verify_runtime()
    return {
        "ok": verification["ok"],
        "phase": "VERIFY_RUNTIME",
        "preflight": pf,
        "verification": verification,
        "deployment_verified": verification["ok"],
    }
