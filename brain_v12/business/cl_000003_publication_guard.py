"""Publication-side enforcement for the CL-000003 cinematic release contract."""
from __future__ import annotations
from typing import Any
from .cl_000003_master_release_gate import decide

def require_master_release(evidence: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        return {"authorized": False, "status": "MASTER_RELEASE_EVIDENCE_REQUIRED"}
    decision = decide(evidence)
    if not decision["publish_authorized"]:
        return {
            "authorized": False,
            "status": "MASTER_RELEASE_PASS_REQUIRED",
            "failures": decision["failures"],
        }
    return {
        "authorized": True,
        "status": "MASTER_RELEASE_AUTHORIZED",
        "identity": decision["identity"],
        "decision_sha256": decision["decision_sha256"],
    }
