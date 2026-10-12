"""Evidence-first legal/human handoff state machine.

This module stores opaque references only. It does not appoint lawyers,
determine heirs, sign mandates, or move money.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Mapping, Any


class HandoffState(str, Enum):
    VERIFIED_FUNDS = "VERIFIED_FUNDS"
    LEGAL_HANDOFF_PENDING = "LEGAL_HANDOFF_PENDING"
    LAWYER_CANDIDATE_REVIEW = "LAWYER_CANDIDATE_REVIEW"
    LAWYER_AUTHORITY_VERIFIED = "LAWYER_AUTHORITY_VERIFIED"
    BENEFICIARY_AUTHORITY_VERIFIED = "BENEFICIARY_AUTHORITY_VERIFIED"
    HUMAN_HANDOFF = "HUMAN_HANDOFF"
    HANDOFF_EVIDENCE_RECORDED = "HANDOFF_EVIDENCE_RECORDED"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"
    DISPUTED = "DISPUTED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


_ALLOWED = {
    HandoffState.VERIFIED_FUNDS: {HandoffState.LEGAL_HANDOFF_PENDING, HandoffState.BLOCKED},
    HandoffState.LEGAL_HANDOFF_PENDING: {HandoffState.LAWYER_CANDIDATE_REVIEW, HandoffState.BLOCKED},
    HandoffState.LAWYER_CANDIDATE_REVIEW: {HandoffState.LAWYER_AUTHORITY_VERIFIED, HandoffState.BLOCKED, HandoffState.REJECTED},
    HandoffState.LAWYER_AUTHORITY_VERIFIED: {HandoffState.BENEFICIARY_AUTHORITY_VERIFIED, HandoffState.BLOCKED, HandoffState.DISPUTED},
    HandoffState.BENEFICIARY_AUTHORITY_VERIFIED: {HandoffState.HUMAN_HANDOFF, HandoffState.BLOCKED, HandoffState.DISPUTED},
    HandoffState.HUMAN_HANDOFF: {HandoffState.HANDOFF_EVIDENCE_RECORDED, HandoffState.DISPUTED},
    HandoffState.HANDOFF_EVIDENCE_RECORDED: {HandoffState.CLOSED},
}


@dataclass
class LegalHandoff:
    founder_identity_ref: str
    state: HandoffState = HandoffState.VERIFIED_FUNDS
    evidence_refs: list[str] = field(default_factory=list)

    def transition(self, new_state: HandoffState, evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if new_state not in _ALLOWED.get(self.state, set()):
            raise ValueError(f"invalid handoff transition: {self.state} -> {new_state}")
        if not self.founder_identity_ref or self.founder_identity_ref.startswith(("Jordan-", "JO-", "NATIONAL-")):
            raise ValueError("identity must be an opaque private reference")
        payload = dict(evidence or {})
        if any(k.lower() in {"national_id", "passport", "account_number", "iban", "private_key", "password"} for k in payload):
            raise ValueError("raw sensitive identity/payment data is forbidden")
        self.state = new_state
        ref = sha256(
            f"{self.founder_identity_ref}|{self.state.value}|{sorted(payload.items())}".encode()
        ).hexdigest()[:24]
        self.evidence_refs.append(ref)
        return {
            "state": self.state.value,
            "founder_identity_ref": self.founder_identity_ref,
            "evidence_ref": ref,
        }
