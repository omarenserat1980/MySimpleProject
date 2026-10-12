"""Auditable unified commercial action gate."""

from __future__ import annotations

from dataclasses import dataclass

from .containment import CommercialContainmentGate
from .decision_audit import DecisionAuditLog
from .policy_guard import CommercialPolicyGuard


@dataclass(frozen=True)
class CommercialActionDecision:
    allowed: bool
    reason: str
    decision_id: str


class AuditedCommercialActionGate:
    def __init__(
        self,
        policy: CommercialPolicyGuard,
        containment: CommercialContainmentGate,
        audit: DecisionAuditLog,
    ) -> None:
        self.policy = policy
        self.containment = containment
        self.audit = audit

    def check(
        self,
        *,
        decision_id: str,
        order_id: str,
        action: str,
        financial_action: bool,
        evidence_present: bool,
        evidence_refs: tuple[str, ...] = (),
    ) -> CommercialActionDecision:
        contained = self.containment.is_contained(order_id)
        decision = self.policy.authorize(
            financial_action=financial_action,
            evidence_present=evidence_present,
            contained=contained,
        )
        self.audit.record(
            decision_id,
            order_id,
            action,
            decision.allowed,
            decision.reason,
            evidence_refs=evidence_refs,
            metadata={
                "financial_action": financial_action,
                "contained": contained,
            },
        )
        return CommercialActionDecision(
            decision.allowed, decision.reason, decision_id
        )
