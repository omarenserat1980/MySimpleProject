from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .engine import QuranicResearchEngine
from .models import EvidenceLevel

class EvidenceIn(BaseModel):
    level: EvidenceLevel
    source: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    citation: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)

class ResearchIn(BaseModel):
    question: str = Field(min_length=1)
    finding: str = Field(min_length=1)
    evidence: list[EvidenceIn] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)

def build_router(engine=None):
    engine = engine or QuranicResearchEngine()
    router = APIRouter(prefix="/api/quranic-core", tags=["quranic-core"])

    @router.get("/health")
    def health():
        return {"ok": True, "module": "Quranic Core", "version": "1.0",
                "integrity_gate": "enabled", "canonical_text_mutation": False}

    @router.get("/research-contract")
    def research_contract(question: str = "كيف يمكن أن ينفع العلم الإنسان؟"):
        return engine.pipeline(question)

    @router.post("/research")
    def research(body: ResearchIn):
        try:
            records = [engine.make_evidence(i.level, i.source, i.claim, i.citation, i.confidence, i.metadata)
                       for i in body.evidence]
            return engine.research(body.question, records, body.finding, body.limitations, body.alternatives).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
