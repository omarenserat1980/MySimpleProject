"""Read-only HTTP interface for Brain Mission Control."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .mission_control import plan

class MissionRequest(BaseModel):
    mission:str=Field(min_length=1)
    evidence_confidence:float=Field(default=0.0, ge=0.0, le=1.0)
    external_side_effects:bool=False

def build_router():
    router=APIRouter(prefix="/api/mission",tags=["mission"])
    @router.post("/plan")
    def mission_plan(body:MissionRequest):
        p=plan(body.mission,body.evidence_confidence,body.external_side_effects)
        return {
            "ok":True,
            "mission":p.mission,
            "mission_fingerprint":p.mission_fingerprint,
            "specialists":list(p.route.specialists),
            "route_reason":p.route.reason,
            "action":p.action,
            "state": ("AUTHORIZATION_REQUIRED" if p.requires_authorization else ("RESEARCHING" if p.action=="RESEARCH" else ("ANALYZING" if p.action=="ANALYZE" else "HOLD"))),
            "external_side_effects":p.external_side_effects,
            "requires_authorization":p.requires_authorization,
            "decision_evidence":p.decision_evidence.canonical(),
            "decision_evidence_fingerprint":p.decision_evidence.fingerprint(),
            "decision_evidence_valid":p.decision_evidence.valid(),
        }
    return router
