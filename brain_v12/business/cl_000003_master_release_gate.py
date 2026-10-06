"""Fail-closed, evidence-bound master release decision for CL-000003 films."""
from __future__ import annotations
import hashlib
import json
from typing import Any

REQUIRED = ("technical", "cinematic", "rights", "legal_policy")
IDENTITY_REQUIRED = ("film_id", "film_version", "production_run")
EVIDENCE_REQUIRED = ("evidence_ref", "evidence_sha256")

def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def decide(evidence: dict[str, Any]) -> dict[str, Any]:
    failures = []
    states = {}
    identity = {k: str(evidence.get(k) or "").strip() for k in IDENTITY_REQUIRED}
    for key, value in identity.items():
        if not value:
            failures.append(f"{key.upper()}_REQUIRED")
    for key in REQUIRED:
        item = evidence.get(key)
        passed = isinstance(item, dict) and item.get("passed") is True
        states[key] = "PASS" if passed else "FAIL"
        if not passed:
            failures.append(f"{key.upper()}_PASS_REQUIRED")
            continue
        for field in EVIDENCE_REQUIRED:
            if not str(item.get(field) or "").strip():
                failures.append(f"{key.upper()}_{field.upper()}_REQUIRED")
        supplied = str(item.get("evidence_sha256") or "").strip().lower()
        if supplied and len(supplied) != 64:
            failures.append(f"{key.upper()}_EVIDENCE_HASH_INVALID")
    release = not failures
    decision = {
        "status": "MASTER_RELEASE_PASS" if release else "DO_NOT_PUBLISH",
        "publish_authorized": release,
        "gates": states,
        "failures": failures,
        "next_action": "PUBLISH" if release else "DIAGNOSE_REWORK_REPLACE",
        "identity": identity,
    }
    decision["decision_sha256"] = _digest(decision)
    return decision
