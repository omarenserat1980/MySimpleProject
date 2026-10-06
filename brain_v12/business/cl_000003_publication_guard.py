"""Publication-side enforcement for the CL-000003 cinematic release contract."""
from __future__ import annotations
from typing import Any

def require_master_release(evidence: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        return {"authorized": False, "status": "MASTER_RELEASE_EVIDENCE_REQUIRED"}
    if evidence.get("status") != "MASTER_RELEASE_PASS":
        return {"authorized": False, "status": "MASTER_RELEASE_PASS_REQUIRED"}
    if evidence.get("publish_authorized") is not True:
        return {"authorized": False, "status": "PUBLISH_AUTHORIZATION_REQUIRED"}
    identity = evidence.get("identity") or {}
    if not all(str(identity.get(k) or "").strip() for k in ("film_id", "film_version", "production_run")):
        return {"authorized": False, "status": "FILM_IDENTITY_REQUIRED"}
    return {"authorized": True, "status": "MASTER_RELEASE_AUTHORIZED", "identity": identity}
