"""Read-only multidisciplinary intelligence API."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .control_plane import DomainSignal, synthesize
from .evidence_registry import Evidence, validate

router=APIRouter(prefix="/api/intelligence",tags=["intelligence"])

class SignalInput(BaseModel):
    domain:str
    confidence:float=Field(ge=0,le=1)
    evidence_count:int=Field(ge=0)
    risk:float=Field(ge=0,le=1)

class EvidenceInput(BaseModel):
    evidence_id:str
    domain:str
    claim:str
    source_ref:str
    observed_at:str
    confidence:float=Field(ge=0,le=1)

class IntelligenceInput(BaseModel):
    signals:list[SignalInput]=Field(default_factory=list)
    evidence:list[EvidenceInput]=Field(default_factory=list)

@router.post("/evaluate")
def evaluate(payload:IntelligenceInput):
    signals=tuple(DomainSignal(s.domain,s.confidence,s.evidence_count,s.risk) for s in payload.signals)
    result=synthesize(signals)
    evidence=[]
    for e in payload.evidence:
        item=Evidence(e.evidence_id,e.domain,e.claim,e.source_ref,e.observed_at,e.confidence)
        if not validate(item): raise ValueError("invalid evidence")
        evidence.append({"evidence_id":e.evidence_id,"fingerprint":item.fingerprint()})
    return {
        "action":result.action.value,
        "confidence":result.confidence,
        "domains":result.domains,
        "rationale":result.rationale,
        "evidence":evidence,
        "external_side_effects":False,
    }
