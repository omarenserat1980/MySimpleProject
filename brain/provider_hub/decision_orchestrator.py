"""Unified commercial decision orchestrator."""

from __future__ import annotations

from dataclasses import dataclass

from .containment import CommercialContainmentGate
from .decision_audit import DecisionAuditLog
from .policy_guard import CommercialPolicyGuard
from .risk_gate import CommercialRiskGate


@dataclass(frozen=True)
class OrchestratedDecision:
    decision_id: str
    order_id: str
    allowed: bool
    reason: str
    risk_score: int
    risk_level: str


class CommercialDecisionOrchestrator:
    def __init__(
        self,
        policy: CommercialPolicyGuard,
        containment: CommercialContainmentGate,
        risk: CommercialRiskGate,
        audit: DecisionAuditLog,
    ) -> None:
        self.policy = policy
        self.containment = containment
        self.risk = risk
        self.audit = audit

    def decide(
        self,
        *,
        decision_id: str,
        order_id: str,
        action: str,
        financial_action: bool,
        evidence_present: bool,
        operational_risk: int,
        evidence_score: int,
        return_score: int,
    ) -> OrchestratedDecision:
        contained = self.containment.is_contained(order_id)
        policy_decision = self.policy.authorize(
            financial_action=financial_action,
            evidence_present=evidence_present,
            contained=contained,
        )
        assessment = self.risk.assess(
            operational_risk=operational_risk,
            evidence_score=evidence_score,
            return_score=return_score,
        )

        if not policy_decision.allowed:
            allowed, reason = False, policy_decision.reason
        else:
            risk_decision = self.risk.decide(
                assessment,
                authorized=True,
                contained=contained,
                financial_action=financial_action,
                evidence_present=evidence_present,
            )
            allowed, reason = risk_decision.allowed, risk_decision.reason

        self.audit.record(
            decision_id,
            order_id,
            action,
            allowed,
            reason,
            metadata={
                "risk_score": assessment.score,
                "risk_level": assessment.level,
                "operational_risk": operational_risk,
                "evidence_score": evidence_score,
                "return_score": return_score,
            },
        )
        return OrchestratedDecision(
            decision_id, order_id, allowed, reason,
            assessment.score, assessment.level,
        )
