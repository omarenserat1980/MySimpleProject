"""Policy guard for sensitive commercial operations.

Separates operational safety from authorization and financial evidence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommercialPolicy:
    financial_action_authorized: bool = False
    payment_evidence_required: bool = True
    contained_orders_blocked: bool = True


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class CommercialPolicyGuard:
    def __init__(self, policy: CommercialPolicy | None = None) -> None:
        self.policy = policy or CommercialPolicy()

    def authorize(
        self,
        financial_action: bool = False,
        evidence_present: bool = False,
        contained: bool = False,
    ) -> PolicyDecision:
        # Keep the contract backward-compatible with older callers while
        # The three explicit parameters intentionally accept both positional and keyword callers.
        if contained and self.policy.contained_orders_blocked:
            return PolicyDecision(False, "ORDER_CONTAINED")
        if financial_action and not self.policy.financial_action_authorized:
            return PolicyDecision(False, "FINANCIAL_AUTHORIZATION_REQUIRED")
        if financial_action and self.policy.payment_evidence_required and not evidence_present:
            return PolicyDecision(False, "FINANCIAL_EVIDENCE_REQUIRED")
        return PolicyDecision(True, "AUTHORIZED")
