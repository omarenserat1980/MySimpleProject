"""Central mission control: deterministic, auditable, permission-safe planning."""
from dataclasses import dataclass
import hashlib
from .mission_router import MissionRoute, route
from .cross_domain_contract import CrossDomainOpportunity, safe_action
from .decision_evidence import DecisionEvidence
from .mission_lifecycle import MissionState

@dataclass(frozen=True)
class MissionPlan:
    mission:str
    route:MissionRoute
    action:str
    external_side_effects:bool
    requires_authorization:bool
    mission_fingerprint:str
    decision_evidence:DecisionEvidence

def fingerprint(mission:str)->str:
    return hashlib.sha256(mission.strip().encode("utf-8")).hexdigest()

def plan(mission:str, evidence_confidence:float=0.0, external_side_effects:bool=False)->MissionPlan:
    if not mission or not mission.strip():
        raise ValueError("mission required")
    r=route(mission)
    mf=fingerprint(mission)
    opportunity=CrossDomainOpportunity(
        opportunity_id="mission:"+mf[:16],
        domains=r.specialists,
        evidence_confidence=evidence_confidence,
        external_side_effects=external_side_effects,
        revenue_verified=False,
        authorized=False,
    )
    action=safe_action(opportunity)
    requires=(action=="AUTHORIZATION_REQUIRED")
    evidence=DecisionEvidence(
        mission_fingerprint=mf,
        action=action,
        specialists=r.specialists,
        evidence_confidence=evidence_confidence,
        external_side_effects=external_side_effects,
        requires_authorization=requires,
        rationale=r.reason,
    )
    return MissionPlan(mission,r,action,external_side_effects,requires,mf,evidence)
