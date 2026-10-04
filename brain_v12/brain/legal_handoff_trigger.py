"""Financial-to-legal handoff trigger.

When independently verified positive funds exist, Brain may prepare a lawyer
handoff request. It never selects a lawyer, sends funds, or invents beneficiary
authority. Actual contact and transfer remain subject to verified legal authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .legal_handoff import HandoffState, LegalHandoff


@dataclass(frozen=True)
class VerifiedFundsTrigger:
    available_funds_verified: bool
    available_amount: float | None
    currency: str
    evidence_refs: tuple[str, ...]
    contracting_authority_verified: bool = False


def prepare_lawyer_request(
    handoff: LegalHandoff,
    trigger: VerifiedFundsTrigger,
    *,
    lawyer_contact_ref: str | None = None,
) -> dict[str, Any]:
    """Open the legal handoff only when positive verified funds exist.

    lawyer_contact_ref is an opaque private reference. No personal contact,
    account, identity, or beneficiary data is returned.
    """
    if not trigger.available_funds_verified:
        return {"status": "BLOCKED", "reason": "VERIFIED_FUNDS_REQUIRED"}
    if trigger.available_amount is None or trigger.available_amount <= 0:
        return {"status": "BLOCKED", "reason": "POSITIVE_VERIFIED_FUNDS_REQUIRED"}
    if not trigger.evidence_refs:
        return {"status": "BLOCKED", "reason": "FUNDING_EVIDENCE_REQUIRED"}
    if not trigger.contracting_authority_verified:
        return {"status": "BLOCKED", "reason": "LEGAL_AUTHORITY_REQUIRED"}
    if handoff.state != HandoffState.VERIFIED_FUNDS:
        return {"status": "BLOCKED", "reason": f"INVALID_START_STATE:{handoff.state.value}"}

    event = handoff.transition(
        HandoffState.LEGAL_HANDOFF_PENDING,
        {"funding_refs": ",".join(sorted(trigger.evidence_refs))},
    )
    return {
        "status": "LAWYER_REQUEST_READY" if lawyer_contact_ref else "LAWYER_CONTACT_REQUIRED",
        "state": event["state"],
        "evidence_ref": event["evidence_ref"],
        "lawyer_contact_ref": lawyer_contact_ref,
        "requested_action": "Verify legal authority and arrange lawful transfer of verified funds",
        "transfer_initiated": False,
    }
