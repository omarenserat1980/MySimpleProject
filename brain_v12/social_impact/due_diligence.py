"""Nonprofit due-diligence scoring."""
from dataclasses import dataclass

@dataclass(frozen=True)
class DueDiligence:
    identity_verified:bool
    governance_evidence:bool
    financial_reporting:bool
    program_evidence:bool
    safeguarding_policy:bool
    conflicts_disclosed:bool

def score(x:DueDiligence)->float:
    return sum(bool(v) for v in (
        x.identity_verified,x.governance_evidence,x.financial_reporting,
        x.program_evidence,x.safeguarding_policy,x.conflicts_disclosed
    ))/6

def suitable_for_partnership(x:DueDiligence)->bool:
    return score(x)>=.83 and x.safeguarding_policy and x.financial_reporting
