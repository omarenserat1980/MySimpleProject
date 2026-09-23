"""Charity and humanitarian-aid intelligence for Jordan and other markets.

Evidence-first directory and eligibility reasoning. This module does not promise
aid, fabricate eligibility, submit applications, or impersonate an applicant.
Current program details must be verified from the organization before action.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AidProgram:
    organization: str
    country: str
    aid_type: str
    official_url: str
    eligibility_notes: str
    evidence_date: str
    evidence_source: str


def classify_aid_program(program: AidProgram) -> str:
    """Return a neutral category useful for opportunity/aid research."""
    if not program.organization or not program.official_url:
        return "INSUFFICIENT_EVIDENCE"
    return "EVIDENCE_RECORDED"


JORDAN_REFERENCES = (
    AidProgram(
        organization="National Aid Fund (NAF)",
        country="Jordan",
        aid_type="cash/social protection",
        official_url="https://www.naf.gov.jo/",
        eligibility_notes="Eligibility and payment depend on current NAF program rules and applicant assessment.",
        evidence_date="2026-09",
        evidence_source="World Bank / official NAF references",
    ),
    AidProgram(
        organization="Jordanian Zakat Fund",
        country="Jordan",
        aid_type="financial and in-kind assistance",
        official_url="https://www.awqaf.gov.jo/EN/Pages/Jordanian_Zakat_Fund",
        eligibility_notes="Provides assistance to needy families and other support programs; current eligibility must be checked with the Fund.",
        evidence_date="2026-09",
        evidence_source="Jordan Ministry of Awqaf and Islamic Affairs",
    ),
)


def research_targets(country: str = "Jordan") -> tuple[str, ...]:
    return (
        "government cash assistance",
        "zakat and charitable assistance",
        "emergency cash assistance",
        "food and rent assistance",
        "disability and medical support",
        "orphan and family support",
        "NGO humanitarian cash programs",
        "employment and livelihood grants",
    )
