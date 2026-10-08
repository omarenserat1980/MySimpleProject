"""Cross-domain contract: opportunities require evidence and permission-safe actions."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CrossDomainOpportunity:
    opportunity_id:str
    domains:tuple[str,...]
    evidence_confidence:float
    external_side_effects:bool=False
    revenue_verified:bool=False

def validate(o:CrossDomainOpportunity)->bool:
    if not o.opportunity_id or not o.domains: return False
    if not 0<=o.evidence_confidence<=1: return False
    if o.external_side_effects and not o.revenue_verified:
        return False
    return True

def safe_action(o:CrossDomainOpportunity)->str:
    if not validate(o): return "HOLD"
    if o.external_side_effects: return "AUTHORIZATION_REQUIRED"
    if o.evidence_confidence<.70: return "RESEARCH"
    return "ANALYZE"
