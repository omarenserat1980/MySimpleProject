"""Operational principles inspired by Quranic descriptions.

This module is an engineering abstraction, not executable theology or a claim
that Brain possesses spiritual attributes.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Principle:
    key: str
    arabic: str
    source: str
    rule: str

PRINCIPLES = (
    Principle("tathabbut","التثبت","الحجرات 49:6","Do not promote unverified reports to facts; verify before consequential action."),
    Principle("amanah","الأمانة","النساء 4:58","Track entrusted data, permissions and commitments; return them to their rightful owner."),
    Principle("adl","العدل","النساء 4:58; النحل 16:90","Require consistent evidence-based treatment and record the basis of consequential decisions."),
    Principle("shura","الشورى","الشورى 42:38","For multi-agent disagreement, collect independent views and evidence before deciding."),
    Principle("ihsan","الإحسان","النحل 16:90","When safe and feasible, improve a merely passing result rather than stopping at minimum validity."),
    Principle("muraqabah","المراجعة","الحشر 59:18","Review what the system has prepared before executing consequential work."),
    Principle("ruju","الرجوع والإصلاح","الزمر 39:53","Treat detected failure as a trigger for repair, revalidation and learning."),
)

def classify_evidence(claim: str, *, verified: bool, source: str | None = None) -> dict:
    return {
        "claim": claim,
        "status": "VERIFIED" if verified else "UNVERIFIED",
        "source": source,
        "requires_verification": not verified,
    }

def governance_check(*, verified: bool, entrusted_data: bool = False,
                     fair_basis: bool = True, disagreement: bool = False,
                     consequential: bool = False) -> dict:
    checks = {
        "tathabbut": verified,
        "amanah": not entrusted_data,
        "adl": fair_basis,
        "shura": not disagreement,
        "muraqabah": not consequential,
    }
    review = [k for k, ok in checks.items() if not ok]
    return {
        "allowed_to_proceed": not review,
        "review_required": review,
        "principles": [p.key for p in PRINCIPLES],
    }
