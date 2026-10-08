from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .engine import QuranicResearchEngine
from .models import EvidenceLevel
from .canonical import CanonicalQuranAdapter
from .tafsir import TafsirAdapter
from .counter_evidence import CounterEvidenceEngine
from .benefit import HumanBenefitEngine
from .orchestrator import QuranicResearchOrchestrator
from .graph import EvidenceGraph
from .publication import PublicationGate
from .research_packet import ResearchPacketBuilder

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
    engine=engine or QuranicResearchEngine()
    canonical=CanonicalQuranAdapter()
    tafsir=TafsirAdapter(canonical)
    counter_engine=CounterEvidenceEngine()
    benefit_engine=HumanBenefitEngine()
    orchestrator=QuranicResearchOrchestrator()
    graph=EvidenceGraph()
    publication=PublicationGate()
    packets=ResearchPacketBuilder(publication)
    router=APIRouter(prefix="/api/quranic-core",tags=["quranic-core"])

    @router.get("/health")
    def health():
        return {"ok":True,"module":"Quranic Core","version":"1.1",
                "integrity_gate":"enabled","orchestrator":"enabled",
                "canonical_text_mutation":False}

    @router.get("/research-contract")
    def research_contract(question:str="كيف يمكن أن ينفع العلم الإنسان؟"):
        return orchestrator.plan(question)

    @router.post("/orchestrate")
    def orchestrate(body:ResearchIn):
        try:
            return orchestrator.evaluate(body.question,body.finding,[x.model_dump() for x in body.evidence])
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc

    @router.post("/decision")
    def decision(body:ResearchIn):
        try:
            result=orchestrator.evaluate(body.question,body.finding,[x.model_dump() for x in body.evidence])
            return orchestrator.decision(result)
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc

    @router.post("/evidence-graph")
    def evidence_graph(body:ResearchIn):
        records=[engine.make_evidence(i.level,i.source,i.claim,i.citation,i.confidence,i.metadata) for i in body.evidence]
        finding=engine.research(body.question,records,body.finding,body.limitations,body.alternatives)
        return graph.build(finding)

    @router.post("/publication-gate")
    def publication_gate(body:ResearchIn):
        records=[engine.make_evidence(i.level,i.source,i.claim,i.citation,i.confidence,i.metadata) for i in body.evidence]
        finding=engine.research(body.question,records,body.finding,body.limitations,body.alternatives)
        return publication.evaluate(finding)

    @router.post("/research-packet")
    def research_packet(body:ResearchIn):
        records=[engine.make_evidence(i.level,i.source,i.claim,i.citation,i.confidence,i.metadata) for i in body.evidence]
        finding=engine.research(body.question,records,body.finding,body.limitations,body.alternatives)
        return packets.build(finding)

    @router.get("/sources/status")
    def sources_status():
        return {"ok":True,"canonical":canonical.configured(),
                "quran_foundation":"configured" if canonical.configured() else "not_configured",
                "tafsir":"available_through_canonical_adapter",
                "scientific":"explicit_evidence_records_only",
                "counter_evidence":"enabled","human_benefit":"enabled"}

    @router.get("/sources/chapters")
    def source_chapters(): return canonical.chapters()

    @router.get("/sources/search")
    def source_search(query:str): return canonical.search(query)

    @router.get("/sources/tafsirs")
    def source_tafsirs(language:str="ar"): return tafsir.resources(language)

    @router.get("/benefit")
    def benefit(finding:str): return benefit_engine.propose(finding)

    @router.post("/counter-evidence")
    def counter_evidence(body:ResearchIn):
        records=[engine.make_evidence(i.level,i.source,i.claim,i.citation,i.confidence,i.metadata) for i in body.evidence]
        return counter_engine.evaluate(body.finding,records)

    @router.post("/research")
    def research(body:ResearchIn):
        try:
            records=[engine.make_evidence(i.level,i.source,i.claim,i.citation,i.confidence,i.metadata) for i in body.evidence]
            return engine.research(body.question,records,body.finding,body.limitations,body.alternatives).to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=422,detail=str(exc)) from exc

    return router
