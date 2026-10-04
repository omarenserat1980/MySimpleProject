"""Integrated commercial decision pipeline."""

from __future__ import annotations
from dataclasses import dataclass
from .containment import CommercialContainmentGate
from .decision_audit import DecisionAuditLog
from .policy_guard import CommercialPolicyGuard
from .risk_gate import CommercialRiskGate
from .secure_human_approval import AuditedSecureApprovalService, SecureHumanApprovalGate

@dataclass(frozen=True)
class IntegratedDecision:
    decision_id: str
    order_id: str
    allowed: bool
    reason: str
    risk_score: int
    risk_level: str

class CommercialExecutionPipeline:
    def __init__(self, containment: CommercialContainmentGate, policy: CommercialPolicyGuard, risk: CommercialRiskGate, decisions: DecisionAuditLog, approvals: SecureHumanApprovalGate | None = None) -> None:
        self.containment, self.policy, self.risk, self.decisions = containment, policy, risk, decisions
        self.approvals = approvals or SecureHumanApprovalGate()

    def decide(self, decision_id: str, order_id: str, action: str, *, financial_action: bool, authorized: bool, evidence_present: bool, operational_risk: int, evidence_score: int, return_score: int, approval_request_id: str | None = None) -> IntegratedDecision:
        if self.containment.is_contained(order_id):
            result = IntegratedDecision(decision_id, order_id, False, "ORDER_CONTAINED", 100, "HIGH")
            self._audit(result, action)
            return result

        policy_decision = self.policy.authorize(financial_action, evidence_present, False)
        if not policy_decision.allowed:
            result = IntegratedDecision(decision_id, order_id, False, policy_decision.reason, 100, "HIGH")
            self._audit(result, action)
            return result

        if financial_action and not authorized:
            result = IntegratedDecision(decision_id, order_id, False, "FINANCIAL_AUTHORIZATION_REQUIRED", 100, "HIGH")
            self._audit(result, action)
            return result

        risk = self.risk.assess(operational_risk, evidence_score, return_score)
        if risk.level == "HIGH":
            if not approval_request_id or not self.approvals.is_approved(approval_request_id):
                result = IntegratedDecision(decision_id, order_id, False, "HUMAN_APPROVAL_REQUIRED", risk.score, risk.level)
                self._audit(result, action)
                return result
            try:
                AuditedSecureApprovalService(self.approvals, self.decisions).consume_for_action(approval_request_id, f"{decision_id}:approval")
            except (KeyError, RuntimeError) as exc:
                result = IntegratedDecision(decision_id, order_id, False, str(exc), risk.score, risk.level)
                self._audit(result, action)
                return result

        result = IntegratedDecision(decision_id, order_id, True, "ALLOWED", risk.score, risk.level)
        self._audit(result, action)
        return result

    def _audit(self, result: IntegratedDecision, action: str) -> None:
        self.decisions.record(result.decision_id, result.order_id, action, result.allowed, result.reason, metadata={"risk_score": result.risk_score, "risk_level": result.risk_level})
