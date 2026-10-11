from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from ..control_auth import require_control_key
from .engine import QuranicResearchEngine
from .models import EvidenceLevel
from .canonical import CanonicalQuranAdapter
from .tafsir import TafsirAdapter
from .counter_evidence import CounterEvidenceEngine
from .benefit import HumanBenefitEngine
from .orchestrator import QuranicResearchOrchestrator
from .graph import EvidenceGraph
from .publication import PublicationGate
from .knowledge import KnowledgeOpportunityEngine
from .research_packet import ResearchPacketBuilder
from .memory_guidance import principles as memory_principles, review_memory

class EvidenceIn(BaseModel):
    level: EvidenceLevel
    source: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    citation: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)

class MemoryReviewIn(BaseModel):
    memory_text: str = Field(min_length=1, max_length=12000)

class StoredMemoryReviewIn(BaseModel):
    memory_key: str = Field(min_length=1, max_length=512)

class MemoryEvidenceIn(BaseModel):
    memory_key: str = Field(min_length=1, max_length=512)
    claim: str = Field(min_length=1, max_length=12000)
    source: str = Field(min_length=1, max_length=2048)
    confidence: float = Field(ge=0.0, le=1.0)
    observed_at: str | None = None
    metadata: dict = Field(default_factory=dict)

class ResearchIn(BaseModel):
    question: str = Field(min_length=1)
    finding: str = Field(min_length=1)
    evidence: list[EvidenceIn] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)

def build_router(engine=None, memory_store=None):
    engine=engine or QuranicResearchEngine()
    canonical=CanonicalQuranAdapter()
    tafsir=TafsirAdapter(canonical)
    counter_engine=CounterEvidenceEngine()
    benefit_engine=HumanBenefitEngine()
    orchestrator=QuranicResearchOrchestrator()
    graph=EvidenceGraph()
    publication=PublicationGate()
    knowledge=KnowledgeOpportunityEngine()
    packets=ResearchPacketBuilder(publication)
    router=APIRouter(prefix="/api/quranic-core",tags=["quranic-core"])

    @router.get("/memory-guidance")
    def quranic_memory_guidance():
        """Return source-linked, read-only principles for reviewing Brain memory."""
        return {
            "ok": True,
            "status": "READ_ONLY_GUIDANCE",
            "count": len(memory_principles()),
            "principles": memory_principles(),
            "memory_mutated": False,
        }

    @router.post("/memory-guidance/review")
    def quranic_memory_review(body: MemoryReviewIn):
        """Suggest review lenses for one memory; never writes to operational memory."""
        return review_memory(body.memory_text)

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

    @router.post("/knowledge-opportunities")
    def knowledge_opportunities(body:ResearchIn):
        records=[engine.make_evidence(i.level,i.source,i.claim,i.citation,i.confidence,i.metadata) for i in body.evidence]
        finding=engine.research(body.question,records,body.finding,body.limitations,body.alternatives)
        return knowledge.generate(finding)

    @router.post("/memory-guidance/review-stored")
    def review_stored_memory(request: Request, body: StoredMemoryReviewIn):
        require_control_key(request)
        if memory_store is None:
            raise HTTPException(status_code=503, detail="MEMORY_STORE_NOT_CONFIGURED")
        record = memory_store.get_memory(body.memory_key)
        if record is None:
            raise HTTPException(status_code=404, detail="MEMORY_KEY_NOT_FOUND")
        review = review_memory(record["value"])
        evidence = memory_store.memory_evidence(body.memory_key)
        conflicts = memory_store.memory_evidence_conflicts(body.memory_key)
        return {
            **review,
            "memory_key": body.memory_key,
            "memory_updated_at": record["updated_at"],
            "evidence": evidence,
            "potential_conflicts": conflicts,
            "memory_mutated": False,
        }

    @router.post("/memory-guidance/evidence")
    def record_memory_evidence(request: Request, body: MemoryEvidenceIn):
        require_control_key(request)
        if memory_store is None:
            raise HTTPException(status_code=503, detail="MEMORY_STORE_NOT_CONFIGURED")
        if memory_store.get_memory(body.memory_key) is None:
            raise HTTPException(status_code=404, detail="MEMORY_KEY_NOT_FOUND")
        item = memory_store.add_memory_evidence(
            body.memory_key, body.claim, body.source, body.confidence,
            observed_at=body.observed_at, metadata=body.metadata,
        )
        return {
            "ok": True,
            "evidence": item,
            "potential_conflicts": memory_store.memory_evidence_conflicts(body.memory_key),
            "memory_mutated": False,
        }

    @router.get("/memory-guidance/evidence")
    def get_memory_evidence(request: Request, memory_key: str):
        require_control_key(request)
        if memory_store is None:
            raise HTTPException(status_code=503, detail="MEMORY_STORE_NOT_CONFIGURED")
        if memory_store.get_memory(memory_key) is None:
            raise HTTPException(status_code=404, detail="MEMORY_KEY_NOT_FOUND")
        return {
            "ok": True,
            "memory_key": memory_key,
            "evidence": memory_store.memory_evidence(memory_key),
            "potential_conflicts": memory_store.memory_evidence_conflicts(memory_key),
        }

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
