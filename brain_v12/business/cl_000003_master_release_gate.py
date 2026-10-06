"""Fail-closed master release decision for CL-000003 films."""
from __future__ import annotations
from typing import Any

REQUIRED = ("technical", "cinematic", "rights", "legal_policy")

def decide(evidence: dict[str, Any]) -> dict[str, Any]:
    failures = []
    states = {}
    for key in REQUIRED:
        item = evidence.get(key)
        passed = isinstance(item, dict) and item.get("passed") is True
        states[key] = "PASS" if passed else "FAIL"
        if not passed:
            failures.append(f"{key.upper()}_PASS_REQUIRED")
    release = not failures
    return {
        "status": "MASTER_RELEASE_PASS" if release else "DO_NOT_PUBLISH",
        "publish_authorized": release,
        "gates": states,
        "failures": failures,
        "next_action": "PUBLISH" if release else "DIAGNOSE_REWORK_REPLACE",
    }
