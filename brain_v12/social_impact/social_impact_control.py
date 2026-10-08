"""Unified social-impact control gate."""
from dataclasses import dataclass
from enum import Enum

class ImpactAction(str,Enum):
    RESEARCH="RESEARCH"; DESIGN="DESIGN"; PARTNER="PARTNER"; FUNDRAISE="FUNDRAISE"; MEASURE="MEASURE"; HOLD="HOLD"

@dataclass(frozen=True)
class ImpactControl:
    evidence_confidence:float
    safeguarding_risk:float
    program_readiness:float
    organization_due_diligence:float
    funding_fit:float

def decide(x:ImpactControl)->ImpactAction:
    vals=(x.evidence_confidence,x.safeguarding_risk,x.program_readiness,x.organization_due_diligence,x.funding_fit)
    if any(v<0 or v>1 for v in vals): raise ValueError("scores must be 0..1")
    if x.safeguarding_risk>.35: return ImpactAction.HOLD
    if x.evidence_confidence<.60: return ImpactAction.RESEARCH
    if x.program_readiness<.70 or x.organization_due_diligence<.70: return ImpactAction.DESIGN
    if x.funding_fit<.70: return ImpactAction.MEASURE
    return ImpactAction.PARTNER
