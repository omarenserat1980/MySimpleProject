"""Read-only Marketing Expert API."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from .marketing_expert import MarketingEvidence
from .marketing_council import convene

router=APIRouter(prefix="/api/marketing",tags=["marketing"])

class EvidenceInput(BaseModel):
    source:str
    metric:str
    value:float
    confidence:float=Field(ge=0,le=1)
    sample_size:int=Field(default=0,ge=0)

class CouncilInput(BaseModel):
    question:str
    evidence:list[EvidenceInput]=Field(default_factory=list)

@router.post("/expert/evaluate")
def evaluate(body:CouncilInput):
    evidence=tuple(MarketingEvidence(x.source,x.metric,x.value,x.confidence,x.sample_size) for x in body.evidence)
    result=convene(body.question,evidence=evidence)
    return {
        "ok":True,
        "question":result.question,
        "specialists":[x.domain for x in result.specialists],
        "action":result.decision.action.value,
        "hypothesis":result.decision.hypothesis,
        "success_metric":result.decision.success_metric,
        "confidence":result.decision.confidence,
        "rationale":result.decision.rationale,
        "external_side_effects":False,
    }
