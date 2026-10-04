"""Unified gate for sensitive commercial actions."""

from __future__ import annotations

from dataclasses import dataclass

from .containment import CommercialContainmentGate
from .policy_guard import CommercialPolicyGuard


@dataclass(frozen=True)
class CommercialActionDecision:
    allowed: bool
    reason: str


class CommercialActionGate:
    def __init__(
        self,
        policy: CommercialPolicyGuard,
        containment: CommercialContainmentGate,
    ) -> None:
        self.policy = policy
        self.containment = containment

    def check(
        self,
        *,
        order_id: str,
        financial_action: bool,
        evidence_present: bool,
    ) -> CommercialActionDecision:
        contained = self.containment.is_contained(order_id)
        decision = self.policy.authorize(
            financial_action=financial_action,
            evidence_present=evidence_present,
            contained=contained,
        )
        return CommercialActionDecision(decision.allowed, decision.reason)
