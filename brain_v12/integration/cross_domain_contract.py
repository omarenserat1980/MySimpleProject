"""Cross-domain contract: evidence and execution authorization are separate gates."""
from dataclasses import dataclass

@dataclass(frozen=True)
class CrossDomainOpportunity:
    opportunity_id:str
    domains:tuple[str,...]
    evidence_confidence:float
    external_side_effects:bool=False
    revenue_verified:bool=False
    authorized:bool=False

def validate(o:CrossDomainOpportunity)->bool:
    if not o.opportunity_id or not o.domains: return False
    if not 0<=o.evidence_confidence<=1: return False
    return True

def safe_action(o:CrossDomainOpportunity)->str:
    if not validate(o): return "HOLD"
    if o.external_side_effects and not o.authorized: return "AUTHORIZATION_REQUIRED"
    if o.evidence_confidence<.70: return "RESEARCH"
    return "ANALYZE"
