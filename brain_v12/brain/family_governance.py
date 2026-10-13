"""Family oversight policy for future Electronic Brain execution stages.

This module evaluates whether an action needs explicit family approval. It does
not authenticate people; integrations must verify approver identity and consent
out of band before supplying a trusted approval record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

SCHEMA = "electronic-brain.family-governance.v1"

FAMILY_ROLES = frozenset({
    "FAMILY_GUARDIAN",
    "FAMILY_MEMBER",
    "FAMILY_VIEWER",
})

# Actions with outside-world, financial, privacy, or hard-to-reverse impact.
APPROVAL_REQUIRED_ACTIONS = frozenset({
    "external_network",
    "publish",
    "spend_money",
    "create_paid_resource",
    "delete",
    "credentials",
    "system_admin",
    "device_control",
    "share_private_data",
    "real_os_boot",
})
DENIED_ACTIONS = frozenset({
    "bypass_safety_gate",
    "expose_secrets",
    "unapproved_paid_resource",
})


@dataclass(frozen=True)
class FamilyApproval:
    """Approval metadata from a trusted identity/consent integration."""

    approver_role: str
    approved: bool
    consent_reference: str
    identity_verified: bool = False
    scope: str = ""

    def valid_for(self, action: str) -> bool:
        return (
            self.approved
            and self.approver_role == "FAMILY_GUARDIAN"
            and self.identity_verified
            and bool(self.consent_reference.strip())
            and self.scope == action
        )


class FamilyGovernance:
    """Conservative policy gate used before planning or executing risky actions."""

    def evaluate(
        self,
        action: str,
        *,
        risk: str = "low",
        irreversible: bool = False,
        approval: FamilyApproval | None = None,
        simulation_only: bool = False,
    ) -> dict[str, Any]:
        action = action.strip().lower() if isinstance(action, str) else ""
        risk = risk.strip().lower() if isinstance(risk, str) else "high"
        if not action:
            return self._result(False, "INVALID_ACTION", action, "high")

        if action in DENIED_ACTIONS:
            return self._result(False, "POLICY_DENY", action, risk)

        # Family approval must never turn a prohibited action into an allowed one.
        if action == "real_os_boot" and simulation_only:
            return self._result(False, "SIMULATION_ONLY", action, risk)

        requires_approval = (
            action in APPROVAL_REQUIRED_ACTIONS
            or risk in {"high", "critical"}
            or irreversible
        )
        if not requires_approval:
            return self._result(True, "ALLOWED_LOW_RISK", action, risk)

        if approval is None:
            return self._result(False, "FAMILY_APPROVAL_REQUIRED", action, risk,
                                approval_required=True)
        if not approval.valid_for(action):
            return self._result(False, "FAMILY_APPROVAL_INVALID_OR_OUT_OF_SCOPE",
                                action, risk, approval_required=True)
        return self._result(True, "FAMILY_APPROVED", action, risk,
                            approval_required=True,
                            approval_reference=approval.consent_reference)

    @staticmethod
    def _result(
        allowed: bool,
        status: str,
        action: str,
        risk: str,
        *,
        approval_required: bool = False,
        approval_reference: str | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": allowed,
            "schema": SCHEMA,
            "status": status,
            "action": action,
            "risk": risk,
            "approval_required": approval_required,
            "approval_reference": approval_reference,
            "family_role_model": sorted(FAMILY_ROLES),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "enforced_at": "POLICY_EVALUATION_ONLY",
            "authentication_performed": False,
            "real_windows_boot_verified": False,
        }
