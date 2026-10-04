"""Calculated commercial risk gate.

Risk scoring informs decisions but can never override authorization,
containment, or mandatory financial evidence.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAssessment:
    score: int
    level: str
    evidence_score: int
    return_score: int


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str
    assessment: RiskAssessment


class CommercialRiskGate:
    def assess(
        self,
        *,
        operational_risk: int,
        evidence_score: int,
        return_score: int,
    ) -> RiskAssessment:
        values = (operational_risk, evidence_score, return_score)
        if any(v < 0 or v > 100 for v in values):
            raise ValueError("RISK_SCORE_OUT_OF_RANGE")

        score = round((operational_risk * 0.5) + ((100 - evidence_score) * 0.3) + ((100 - return_score) * 0.2))
        level = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH"
        return RiskAssessment(score, level, evidence_score, return_score)

    def decide(
        self,
        assessment: RiskAssessment,
        *,
        authorized: bool,
        contained: bool,
        financial_action: bool,
        evidence_present: bool,
    ) -> RiskDecision:
        if contained:
            return RiskDecision(False, "ORDER_CONTAINED", assessment)
        if not authorized:
            return RiskDecision(False, "AUTHORIZATION_REQUIRED", assessment)
        if financial_action and not evidence_present:
            return RiskDecision(False, "FINANCIAL_EVIDENCE_REQUIRED", assessment)

        # Risk never overrides mandatory gates. For non-financial actions,
        # HIGH risk is a stop/review signal rather than an automatic bypass.
        if assessment.level == "HIGH":
            return RiskDecision(False, "HIGH_RISK_REQUIRES_REVIEW", assessment)

        return RiskDecision(True, "RISK_ACCEPTABLE", assessment)
