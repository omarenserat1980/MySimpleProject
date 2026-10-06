"""Brain industrial-client request contract.

A client may request a bounded Brain-owned operation, but it cannot choose an
arbitrary workflow. The server maps the approved operation to the existing
primary workflow and records the request before dispatch.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any


INDUSTRIAL_CLIENT_ID = "BRAIN-CLIENT-ARKAN-ISO-01"
PRIMARY_WORKFLOW = "372137841"  # Existing Brain Windows Real Boot Evidence workflow ID
ALLOWED_REQUEST = "LOAD_AND_BOOT_BRAIN_ISO"


def _key_hash() -> str:
    return os.getenv("BRAIN_INDUSTRIAL_CLIENT_KEY_SHA256", "").strip().lower()


def authenticate(client_id: str, supplied_key: str) -> bool:
    if client_id != INDUSTRIAL_CLIENT_ID or not supplied_key:
        return False
    expected = _key_hash()
    if not expected:
        return False
    return hmac.compare_digest(
        hashlib.sha256(supplied_key.encode("utf-8")).hexdigest(), expected
    )


def build_request(client_id: str, request: str, target: str = "arkan") -> dict[str, Any]:
    if client_id != INDUSTRIAL_CLIENT_ID:
        return {"ok": False, "status": "UNKNOWN_CLIENT"}
    if request != ALLOWED_REQUEST:
        return {"ok": False, "status": "REQUEST_NOT_ALLOWED"}
    if target != "arkan":
        return {"ok": False, "status": "TARGET_NOT_ALLOWED"}
    return {
        "ok": True,
        "status": "REQUEST_ACCEPTED",
        "client_id": client_id,
        "request": request,
        "target": target,
        "workflow": PRIMARY_WORKFLOW,
        "execution_policy": "EXISTING_PRIMARY_PIPELINE",
        "verification": "WORKFLOW_SUCCESS_AND_WINDOWS_BOOT_EVIDENCE",
    }
