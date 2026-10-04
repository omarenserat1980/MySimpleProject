"""Fail-closed gate for enabling paid external executors.

Paid capability is an optional scaling layer. Core Brain operation never depends
on it. Enabling paid execution requires independently verified company funding
evidence and explicit authorization; this module never moves money.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CommercialFundingEvidence:
    available_funds_verified: bool = False
    available_amount: float | None = None
    currency: str = "USD"
    evidence_refs: list[str] = field(default_factory=list)
    authorized: bool = False


@dataclass(frozen=True)
class CommercialExecutionDecision:
    paid_allowed: bool
    reason: str
    evidence_refs: list[str] = field(default_factory=list)


def evaluate_paid_execution(evidence: CommercialFundingEvidence) -> CommercialExecutionDecision:
    if not evidence.authorized:
        return CommercialExecutionDecision(False, "EXPLICIT_AUTHORIZATION_REQUIRED", list(evidence.evidence_refs))
    if not evidence.available_funds_verified:
        return CommercialExecutionDecision(False, "VERIFIED_FUNDS_REQUIRED", list(evidence.evidence_refs))
    if evidence.available_amount is None or evidence.available_amount <= 0:
        return CommercialExecutionDecision(False, "POSITIVE_VERIFIED_FUNDS_REQUIRED", list(evidence.evidence_refs))
    if not evidence.evidence_refs:
        return CommercialExecutionDecision(False, "FUNDING_EVIDENCE_REQUIRED", [])
    return CommercialExecutionDecision(True, "COMMERCIAL_MODE_ENABLED", list(evidence.evidence_refs))
