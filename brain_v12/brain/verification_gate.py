"""Unified evidence gate for Brain execution results.

The gate separates action-level success from objective completion. A runner may
prove that a command executed successfully, but Brain may claim completion only
when explicit objective verification and non-empty evidence are present.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


class VerificationGate:
    """Turn an execution result into a conservative verification decision."""

    @staticmethod
    def evaluate(result: Mapping[str, Any] | None) -> dict[str, Any]:
        if not isinstance(result, Mapping):
            return {
                "action_verified": False,
                "objective_verified": False,
                "status": "NOT_VERIFIED",
                "reason": "INVALID_RESULT",
                "evidence_ref": None,
            }

        action_verified = result.get("ok") is True and result.get("status") == "COMPLETED"
        objective_verified = result.get("objective_verified") is True

        evidence = result.get("evidence")
        if evidence is None:
            evidence = result.get("verification_evidence")
        has_evidence = evidence not in (None, "", [], {}, False)

        if objective_verified and not has_evidence:
            objective_verified = False
            reason = "OBJECTIVE_VERIFICATION_REQUIRES_EVIDENCE"
        elif objective_verified and not action_verified:
            objective_verified = False
            reason = "OBJECTIVE_VERIFICATION_REQUIRES_COMPLETED_ACTION"
        elif objective_verified:
            reason = "OBJECTIVE_VERIFIED"
        elif action_verified:
            reason = "ACTION_VERIFIED_ONLY"
        else:
            reason = "NOT_VERIFIED"

        evidence_ref = None
        if has_evidence:
            digest = sha256(
                json.dumps(evidence, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
            ).hexdigest()
            evidence_ref = f"evidence://sha256/{digest}"

        return {
            "action_verified": action_verified,
            "objective_verified": objective_verified,
            "status": "VERIFIED" if objective_verified else (
                "ACTION_VERIFIED" if action_verified else "NOT_VERIFIED"
            ),
            "reason": reason,
            "evidence_ref": evidence_ref,
        }

    @classmethod
    def require_objective_verification(cls, result: Mapping[str, Any] | None) -> dict[str, Any]:
        decision = cls.evaluate(result)
        if not decision["objective_verified"]:
            raise VerificationError(decision)
        return decision


class VerificationError(RuntimeError):
    """Raised when an execution result cannot prove objective completion."""

    def __init__(self, decision: Mapping[str, Any]):
        self.decision = dict(decision)
        super().__init__(self.decision["reason"])
