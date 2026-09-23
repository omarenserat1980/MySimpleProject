"""Post-transaction learning gate: only verified outcomes become learning evidence."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Outcome:
    outcome_id: str
    paid_jod: float
    verified: bool
    evidence: str

def accept_outcome(outcome: Outcome) -> dict:
    if not outcome.verified:
        return {"accepted":False,"reason":"UNVERIFIED_OUTCOME","profit_jod":0.0}
    if outcome.paid_jod < 0:
        return {"accepted":False,"reason":"INVALID_AMOUNT","profit_jod":0.0}
    if not outcome.evidence.strip():
        return {"accepted":False,"reason":"EVIDENCE_REQUIRED","profit_jod":0.0}
    return {"accepted":True,"reason":"VERIFIED","profit_jod":round(outcome.paid_jod,2)}
