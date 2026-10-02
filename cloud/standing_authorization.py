"""Standing operator delegation and customer-consent gates."""

from dataclasses import dataclass
from enum import Enum


class Risk(str, Enum):
    ROUTINE = "ROUTINE"
    HIGH_IMPACT = "HIGH_IMPACT"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    REQUIRED = "REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class StandingAuthorization:
    enabled: bool = False
    policy_version: str = "1.0"
    monetary_limit: float = 0.0
    currency: str = "JOD"


@dataclass(frozen=True)
class CustomerConsent:
    approved: bool
    scope_ref: str
    approved_version: str
    approved_amount: float | None = None
    approved_currency: str | None = None
    evidence_ref: str | None = None


def operator_gate(*, authorization: StandingAuthorization, risk: Risk,
                  amount: float | None = None, currency: str | None = None,
                  human_approval: bool = False) -> ApprovalStatus:
    if human_approval:
        return ApprovalStatus.APPROVED
    if not authorization.enabled:
        return ApprovalStatus.REQUIRED
    if risk == Risk.HIGH_IMPACT:
        return ApprovalStatus.REQUIRED
    if amount is not None:
        if currency and currency.upper() != authorization.currency.upper():
            return ApprovalStatus.REQUIRED
        if amount > authorization.monetary_limit:
            return ApprovalStatus.REQUIRED
    return ApprovalStatus.NOT_REQUIRED


def customer_gate(*, required: bool, consent: CustomerConsent | None,
                  scope_ref: str, version: str,
                  amount: float | None = None, currency: str | None = None) -> ApprovalStatus:
    if not required:
        return ApprovalStatus.NOT_REQUIRED
    if consent is None or not consent.approved or not consent.evidence_ref:
        return ApprovalStatus.REQUIRED
    if consent.scope_ref != scope_ref or consent.approved_version != version:
        return ApprovalStatus.REQUIRED
    if amount is not None and consent.approved_amount != amount:
        return ApprovalStatus.REQUIRED
    if currency is not None and (consent.approved_currency or "").upper() != currency.upper():
        return ApprovalStatus.REQUIRED
    return ApprovalStatus.APPROVED


def execution_gate(*, operator_status: ApprovalStatus,
                   customer_status: ApprovalStatus) -> bool:
    return operator_status in {ApprovalStatus.NOT_REQUIRED, ApprovalStatus.APPROVED} and customer_status in {
        ApprovalStatus.NOT_REQUIRED, ApprovalStatus.APPROVED
    }
