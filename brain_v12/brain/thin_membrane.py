"""BRAIN Thin Membrane: read-only configuration and readiness diagnostics.

This module deliberately does not connect to cloud endpoints, enroll devices,
create credentials, execute remote tasks, or mutate network settings.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/api/thin-membrane", tags=["BRAIN Thin Membrane"])


def _configured_url(name: str) -> dict:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {"configured": False, "state": "NOT_CONFIGURED", "scheme": None, "host_present": False}
    try:
        parsed = urlparse(raw)
        valid = parsed.scheme in ("https", "http") and bool(parsed.hostname)
        # HTTP is reported but not considered production-safe. No URL or credentials are returned.
        secure = parsed.scheme == "https" and bool(parsed.hostname)
        return {
            "configured": True,
            "state": "CONFIGURED_TLS" if secure else ("INSECURE_HTTP" if valid else "INVALID_URL"),
            "scheme": parsed.scheme if valid else None,
            "host_present": bool(parsed.hostname) if valid else False,
            "tls_required_satisfied": secure,
        }
    except Exception:
        return {"configured": True, "state": "INVALID_URL", "scheme": None, "host_present": False, "tls_required_satisfied": False}


def thin_membrane_status() -> dict:
    """Return truthful readiness inventory without network I/O or secret disclosure."""
    endpoint = _configured_url("BRAIN_CLOUD_HUB_URL")
    device_id = os.getenv("BRAIN_DEVICE_ID", "").strip()
    auth_configured = bool(
        os.getenv("BRAIN_AGENT_KEY")
        or os.getenv("BRAIN_AGENT_KEY_SHA256")
        or os.getenv("BRAIN_EMULATOR_KEY")
        or os.getenv("BRAIN_EMULATOR_AGENT_KEY")
    )
    key_path = os.path.expanduser(
        os.getenv("BRAIN_AGENT_KEY_FILE") or os.getenv("V12_AGENT_KEY_FILE") or "~/v12-agent/agent.key"
    )
    try:
        auth_configured = auth_configured or (Path(key_path).is_file() and Path(key_path).stat().st_size > 0)
    except OSError:
        pass
    configured_parts = sum((endpoint["configured"], bool(device_id), auth_configured))
    state = "READY_FOR_CONNECTIVITY_TEST" if endpoint.get("tls_required_satisfied") and device_id and auth_configured else "NOT_READY"
    return {
        "ok": True,
        "module": "BRAIN Thin Membrane",
        "version": "1.0",
        "mode": "READ_ONLY_READINESS_DIAGNOSTICS",
        "state": state,
        "device_identity": {"configured": bool(device_id), "value": device_id or None},
        "cloud_endpoint": endpoint,
        "device_authentication": {"configured": auth_configured, "secret_values_returned": False},
        "summary": {
            "required_components": 3,
            "configured_components": configured_parts,
            "connection_verified": False,
            "heartbeat_verified": False,
            "task_roundtrip_verified": False,
        },
        "capabilities": {
            "outbound_tls_design": True,
            "reconnect_policy_implemented_here": False,
            "task_execution_enabled_here": False,
            "cloud_contact_attempted": False,
        },
        "safety": {
            "network_scan_performed": False,
            "router_settings_changed": False,
            "firewall_rules_changed": False,
            "credentials_created_or_rotated": False,
            "production_changed": False,
        },
        "next_required_evidence": [
            "verified TLS connection to approved Brain Cloud endpoint",
            "authenticated device heartbeat",
            "safe task round-trip",
        ],
    }


@router.get("/status")
def thin_membrane_status_route():
    return thin_membrane_status()


@router.get("/connectivity-check")
def connectivity_check(x_brain_membrane_probe: str | None = Header(default=None)):
    """Check only authenticated local API reachability, not cloud connectivity.

    Configure BRAIN_MEMBRANE_PROBE_TOKEN out-of-band to enable this endpoint.
    The probe value must never be stored in the repository or returned.
    """
    expected = os.getenv("BRAIN_MEMBRANE_PROBE_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="PROBE_NOT_CONFIGURED")
    if not x_brain_membrane_probe or x_brain_membrane_probe != expected:
        raise HTTPException(status_code=401, detail="PROBE_AUTH_FAILED")
    return {
        "ok": True,
        "probe": "AUTHENTICATED_LOCAL_API_REACHABILITY",
        "device_cloud_connection_verified": False,
        "device_heartbeat_verified": False,
        "task_roundtrip_verified": False,
        "secret_returned": False,
    }
