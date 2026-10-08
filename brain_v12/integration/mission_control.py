"""Central mission control: route, apply evidence gate, and return a permission-safe plan."""
from dataclasses import dataclass
from .mission_router import MissionRoute, route
from .cross_domain_contract import CrossDomainOpportunity, safe_action

@dataclass(frozen=True)
class MissionPlan:
    mission:str
    route:MissionRoute
    action:str
    external_side_effects:bool
    requires_authorization:bool

def plan(mission:str, evidence_confidence:float=0.0, external_side_effects:bool=False)->MissionPlan:
    r=route(mission)
    opportunity=CrossDomainOpportunity(
        opportunity_id="mission:"+str(abs(hash(mission))),
        domains=r.specialists,
        evidence_confidence=evidence_confidence,
        external_side_effects=external_side_effects,
        revenue_verified=False,
    )
    action=safe_action(opportunity)
    return MissionPlan(
        mission=mission,
        route=r,
        action=action,
        external_side_effects=external_side_effects,
        requires_authorization=(action=="AUTHORIZATION_REQUIRED"),
    )
