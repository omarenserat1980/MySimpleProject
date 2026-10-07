"""Brain-authorized ChatGPT gateway.

This module defines the message envelope exchanged with a ChatGPT tool/runtime.
It does not attempt to automate the ChatGPT mobile UI. The Brain remains the
decision authority; ChatGPT receives a bounded request and returns evidence.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any


PROTOCOL_VERSION = "1.0"


def create_request(
    *,
    decision_id: str,
    request: str,
    objective: str,
    constraints: list[str] | None = None,
    required_evidence: list[str] | None = None,
    allowed_actions: list[str] | None = None,
) -> dict[str, Any]:
    envelope = {
        "protocol": "BRAIN_CHATGPT",
        "protocol_version": PROTOCOL_VERSION,
        "source": "ELECTRONIC_BRAIN",
        "authority": "BRAIN",
        "decision_id": str(decision_id),
        "request": str(request),
        "objective": str(objective),
        "constraints": list(constraints or []),
        "required_evidence": list(required_evidence or []),
        "allowed_actions": list(allowed_actions or []),
        "created_at": time.time(),
    }
    canonical = json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode()
    envelope["request_hash"] = hashlib.sha256(canonical).hexdigest()
    return envelope


def validate_response(request: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Validate the response envelope without treating ChatGPT's claims as proof."""
    if response.get("protocol") != "BRAIN_CHATGPT":
        return {"ok": False, "status": "INVALID_PROTOCOL"}
    if response.get("decision_id") != request.get("decision_id"):
        return {"ok": False, "status": "DECISION_ID_MISMATCH"}
    evidence = response.get("evidence")
    if not isinstance(evidence, list):
        return {"ok": False, "status": "EVIDENCE_REQUIRED"}
    return {
        "ok": True,
        "status": "RECEIVED",
        "decision_id": request["decision_id"],
        "chatgpt_status": response.get("status", "UNKNOWN"),
        "evidence_count": len(evidence),
        "next_action": response.get("next_action"),
        "note": "Brain must independently verify evidence before acceptance.",
    }
