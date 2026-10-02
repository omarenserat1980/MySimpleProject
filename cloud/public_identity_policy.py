"""Policy gates for Brain public identity and personal-liability safeguards."""

from dataclasses import dataclass

BLOCKED_PERSONAL_ACTIONS = frozenset({
    "PERSONAL_GUARANTEE",
    "PERSONAL_BORROWING",
    "PERSONAL_CONTRACT",
    "COMMINGLE_FUNDS",
    "UNDOCUMENTED_PERSONAL_PAYMENT",
    "PERSONAL_DEBT",
})

@dataclass(frozen=True)
class LegalEntityEvidence:
    registration_ref: str | None
    tax_ref: str | None
    licensing_ref: str | None
    invoicing_ref: str | None

def validate_public_operation(*, entity_registered: bool, compliance_ready: bool, human_approval: bool, evidence: LegalEntityEvidence) -> dict:
    missing = []
    if not entity_registered or not evidence.registration_ref:
        missing.append("registration_evidence")
    if not compliance_ready:
        missing.append("compliance_ready")
    if not human_approval:
        missing.append("human_approval")
    if missing:
        return {"ok": False, "state": "ENTITY_PLANNING", "missing": missing}
    return {"ok": True, "state": "PUBLIC_COMMERCIAL_OPERATION", "missing": []}

def validate_personal_action(action: str) -> dict:
    normalized = action.strip().upper()
    if normalized in BLOCKED_PERSONAL_ACTIONS:
        return {"ok": False, "blocked": True, "reason": "Personal liability/commingling action is blocked by default."}
    return {"ok": True, "blocked": False}

def lawful_disclosure_required(party_type: str) -> bool:
    return party_type.strip().upper() in {
        "REGULATOR", "BANK", "PAYMENT_PROVIDER", "TAX_AUTHORITY", "COURT", "AUTHORIZED_AUDITOR",
    }