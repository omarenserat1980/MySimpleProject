"""Economic integrity primitives for evidence-backed revenue settlement.

This module is deterministic and side-effect free. It does not create money;
it decides whether an already supplied payment proof is eligible for settlement.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable

from .revenue_gate import PaymentEvidence


@dataclass(frozen=True)
class RevenueProof:
    opportunity_id: str
    evidence_id: str
    evidence_hash: str
    amount: float
    currency: str
    proof_ref: str


@dataclass(frozen=True)
class IntegrityResult:
    valid: bool
    reason: str
    proof: RevenueProof | None = None


def evidence_fingerprint(evidence: PaymentEvidence) -> str:
    payload = {
        "evidence_id": evidence.evidence_id.strip(),
        "opportunity_id": evidence.opportunity_id.strip(),
        "amount": evidence.amount,
        "currency": evidence.currency.strip().upper(),
        "received_at": evidence.received_at,
        "proof_ref": evidence.proof_ref.strip(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def verify_payment_evidence(
    evidence: PaymentEvidence,
    *,
    existing_evidence_ids: Iterable[str] = (),
    existing_evidence_hashes: Iterable[str] = (),
) -> IntegrityResult:
    if not evidence.is_valid():
        return IntegrityResult(False, "INVALID_PAYMENT_EVIDENCE")
    if not evidence.evidence_id.strip():
        return IntegrityResult(False, "MISSING_EVIDENCE_ID")
    if not evidence.opportunity_id.strip():
        return IntegrityResult(False, "MISSING_OPPORTUNITY_ID")

    fingerprint = evidence_fingerprint(evidence)
    if evidence.evidence_id in set(existing_evidence_ids):
        return IntegrityResult(False, "DUPLICATE_EVIDENCE_ID")
    if fingerprint in set(existing_evidence_hashes):
        return IntegrityResult(False, "DUPLICATE_EVIDENCE_HASH")

    return IntegrityResult(
        True,
        "VALID",
        RevenueProof(
            opportunity_id=evidence.opportunity_id,
            evidence_id=evidence.evidence_id,
            evidence_hash=fingerprint,
            amount=evidence.amount,
            currency=evidence.currency.strip().upper(),
            proof_ref=evidence.proof_ref.strip(),
        ),
    )
