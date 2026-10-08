from __future__ import annotations
from dataclasses import dataclass
from .engine import QuranicResearchEngine
from .counter_evidence import CounterEvidenceEngine
from .benefit import HumanBenefitEngine
from .models import EvidenceLevel

@dataclass
class QuranicResearchOrchestrator:
    engine: QuranicResearchEngine
    counter: CounterEvidenceEngine
    benefit: HumanBenefitEngine

    def __init__(self):
        self.engine=QuranicResearchEngine()
        self.counter=CounterEvidenceEngine()
        self.benefit=HumanBenefitEngine()

    STAGES=("SOURCE_LOCK","LANGUAGE_AND_CONTEXT","TAFSIR_COMPARISON",
            "HUMAN_KNOWLEDGE","SCIENTIFIC_CHECK","COUNTER_EVIDENCE",
            "INTEGRITY_GATE","HUMAN_BENEFIT","PUBLISH_OR_HOLD")

    def plan(self, question:str)->dict:
        return {"ok":True,"question":question.strip(),"stages":list(self.STAGES),
                "policy":"single_orchestrated_path","publish_requires":"integrity_and_counter_evidence"}

    def evaluate(self, question:str, finding:str, evidence:list)->dict:
        records=[]
        for item in evidence:
            records.append(self.engine.make_evidence(
                EvidenceLevel(item["level"]),item["source"],item["claim"],
                item.get("citation"),item.get("confidence",0.0),item.get("metadata")))
        integrity=self.engine.gate.validate(records)
        if not integrity.allowed:
            return {"ok":False,"status":"HOLD","stage":"INTEGRITY_GATE","reasons":list(integrity.reasons)}
        counter=self.counter.evaluate(finding,records)
        # Counter-evidence must be explicitly considered before publication.
        if counter["status"]=="NO_COUNTER_EVIDENCE_RECORDED":
            return {"ok":True,"status":"HOLD","stage":"COUNTER_EVIDENCE",
                    "counter_evidence":counter,
                    "message":"No counter-evidence was recorded; publication is blocked until the challenge stage is completed."}
        benefit=self.benefit.propose(finding)
        return {"ok":True,"status":"READY_FOR_HUMAN_REVIEW","stage":"HUMAN_BENEFIT",
                "question":question,"finding":finding,
                "evidence_count":len(records),"counter_evidence":counter,
                "human_benefit":benefit,
                "next":"human_review_before_publication"}
