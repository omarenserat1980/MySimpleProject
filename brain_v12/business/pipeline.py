"""Evidence-backed sales pipeline with explicit state transitions."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import time

STAGES=("DISCOVERED","QUALIFIED","OFFER_READY","HUMAN_APPROVED","DELIVERING","DELIVERED","PAYMENT_PENDING","PAYMENT_VERIFIED","REVENUE_REALIZED","CLOSED_LOST")

@dataclass
class Opportunity:
    opportunity_id: str
    customer: str
    problem: str
    offer: str
    stage: str = "DISCOVERED"
    evidence: list[str] = field(default_factory=list)
    value_note: str = ""
    created_at: float = field(default_factory=time)
    audit: list[dict] = field(default_factory=list)

    def transition(self, new_stage: str, evidence: str | None = None) -> dict:
        if new_stage not in STAGES:
            raise ValueError("unknown stage")
        guarded={"HUMAN_APPROVED","PAYMENT_VERIFIED","REVENUE_REALIZED"}
        if new_stage in guarded and not evidence:
            raise ValueError(f"evidence required for {new_stage}")
        self.stage=new_stage
        if evidence:
            self.evidence.append(evidence)
        self.audit.append({"stage":new_stage,"evidence":evidence})
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "opportunity_id":self.opportunity_id,"customer":self.customer,
            "problem":self.problem,"offer":self.offer,"stage":self.stage,
            "evidence":self.evidence,"value_note":self.value_note,"audit":self.audit,
        }
