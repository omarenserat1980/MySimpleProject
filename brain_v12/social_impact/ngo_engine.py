"""NGO and social-impact intelligence. Analysis/planning only."""
from dataclasses import dataclass
from enum import Enum

class NGOAction(str,Enum):
    RESEARCH="RESEARCH"; DESIGN="DESIGN"; APPLY="APPLY_READY"; PARTNER="PARTNER"; HOLD="HOLD"

@dataclass(frozen=True)
class NGOOpportunity:
    opportunity_id:str
    organization:str
    cause:str
    country:str
    beneficiary_fit:float
    funding_fit:float
    implementation_fit:float
    evidence_confidence:float
    safeguarding_risk:float=.0

def evaluate(x:NGOOpportunity)->NGOAction:
    vals=(x.beneficiary_fit,x.funding_fit,x.implementation_fit,x.evidence_confidence,x.safeguarding_risk)
    if any(v<0 or v>1 for v in vals): raise ValueError("scores must be 0..1")
    if x.safeguarding_risk>.35: return NGOAction.HOLD
    if x.evidence_confidence<.70: return NGOAction.RESEARCH
    score=.35*x.beneficiary_fit+.25*x.funding_fit+.25*x.implementation_fit+.15*x.evidence_confidence
    if score>=.75: return NGOAction.PARTNER
    if score>=.60: return NGOAction.DESIGN
    return NGOAction.HOLD
