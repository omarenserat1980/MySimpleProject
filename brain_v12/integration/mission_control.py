"""Central mission control: deterministic, auditable, permission-safe planning."""
from dataclasses import dataclass
import hashlib
from .mission_router import MissionRoute, route
from .cross_domain_contract import CrossDomainOpportunity, safe_action

@dataclass(frozen=True)
class MissionPlan:
    mission:str
    route:MissionRoute
    action:str
    external_side_effects:bool
    requires_authorization:bool
    mission_fingerprint:str

def fingerprint(mission:str)->str:
    return hashlib.sha256(mission.strip().encode("utf-8")).hexdigest()

def plan(mission:str, evidence_confidence:float=0.0, external_side_effects:bool=False)->MissionPlan:
    if not mission or not mission.strip():
        raise ValueError("mission required")
    r=route(mission)
    opportunity=CrossDomainOpportunity(
        opportunity_id="mission:"+fingerprint(mission)[:16],
        domains=r.specialists,
        evidence_confidence=evidence_confidence,
        external_side_effects=external_side_effects,
        revenue_verified=False,
        authorized=False,
    )
    action=safe_action(opportunity)
    return MissionPlan(
        mission=mission,
        route=r,
        action=action,
        external_side_effects=external_side_effects,
        requires_authorization=(action=="AUTHORIZATION_REQUIRED"),
        mission_fingerprint=fingerprint(mission),
    )
