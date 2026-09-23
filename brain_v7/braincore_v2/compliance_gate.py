"""Policy gate for external-work actions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str
    requires_user_approval: bool = False


class ComplianceGate:
    BLOCKED = {
        "SPAM", "FAKE_IDENTITY", "BYPASS_VERIFICATION", "CREDENTIAL_SHARING",
        "UNAUTHORIZED_ACCESS", "MONEY_TRANSFER", "WITHDRAW_FUNDS",
        "CONTRACT_SIGNING", "DECEPTIVE_REVIEW", "PLATFORM_EVASION",
    }

    APPROVAL_REQUIRED = {
        "SUBMIT_PROPOSAL", "ACCEPT_ORDER", "PUBLISH_PROFILE_CHANGE",
        "PUBLISH_CONTENT", "CHANGE_PRICING",
    }

    def evaluate(self, action: str, *, authorized: bool = False) -> GateDecision:
        action = action.upper()
        if action in self.BLOCKED:
            return GateDecision(False, f"Blocked policy action: {action}")
        if action in self.APPROVAL_REQUIRED and not authorized:
            return GateDecision(False, "Explicit user/platform authorization required", True)
        return GateDecision(True, "Allowed within configured scope")
