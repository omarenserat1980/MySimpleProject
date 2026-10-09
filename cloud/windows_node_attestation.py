"""Fail-closed identity binding for Windows Cloud Fabric nodes."""
from __future__ import annotations
import hashlib
from typing import Any

def bind_or_verify(node: dict[str, Any], attestation: dict[str, Any]) -> tuple[bool, str]:
    identity = str(attestation.get("guest_identity", "")).strip()
    if not identity:
        return False, "GUEST_IDENTITY_MISSING"
    if not attestation.get("verified_os"):
        return False, "WINDOWS_SERVER_2025_NOT_VERIFIED"
    bound = str(node.get("guest_identity", "")).strip()
    if not bound:
        return True, "IDENTITY_BOUND"
    if not __import__("hmac").compare_digest(bound, identity):
        return False, "GUEST_IDENTITY_DRIFT"
    return True, "IDENTITY_MATCH"

def attestation_evidence(node_id: str, attestation: dict[str, Any]) -> dict[str, Any]:
    identity = str(attestation.get("guest_identity", ""))
    return {
        "type": "WINDOWS_GUEST_IDENTITY_ATTESTATION",
        "node_id": node_id,
        "identity_fingerprint": hashlib.sha256(identity.encode()).hexdigest() if identity else "",
        "verified_os": bool(attestation.get("verified_os")),
        "architecture": attestation.get("architecture"),
        "observed_at": __import__("time").time(),
    }
