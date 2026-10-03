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
    evidence: list = field(default_factory=list)
    value_note: str = ""
    created_at: float = field(default_factory=time)
    audit: list = field(default_factory=list)

    def transition(self, new_stage: str, evidence=None) -> dict:
        if new_stage not in STAGES:
            raise ValueError("unknown stage")

        if new_stage == "PAYMENT_VERIFIED":
            if self.stage != "PAYMENT_PENDING":
                raise ValueError("payment must be pending before verification")
            if not isinstance(evidence, dict):
                raise ValueError("structured payment evidence required")
            transaction_id = str(evidence.get("transaction_id", "")).strip()
            evidence_ref = str(evidence.get("evidence_ref", "")).strip()
            if not transaction_id or not evidence_ref:
                raise ValueError("transaction_id and evidence_ref required")
            stored_evidence = {
                "type": "payment_verification",
                "transaction_id": transaction_id,
                "evidence_ref": evidence_ref,
            }
        elif new_stage == "REVENUE_REALIZED":
            if self.stage != "PAYMENT_VERIFIED":
                raise ValueError("payment must be verified before revenue realization")
            if not isinstance(evidence, dict):
                raise ValueError("structured realization evidence required")
            delivery_ref = str(evidence.get("delivery_evidence_ref", "")).strip()
            reconciliation_ref = str(evidence.get("reconciliation_ref", "")).strip()
            if not delivery_ref or not reconciliation_ref:
                raise ValueError("delivery_evidence_ref and reconciliation_ref required")
            stored_evidence = {
                "type": "revenue_realization",
                "delivery_evidence_ref": delivery_ref,
                "reconciliation_ref": reconciliation_ref,
            }
        elif new_stage == "HUMAN_APPROVED":
            if not isinstance(evidence, str) or not evidence.strip():
                raise ValueError("evidence required for HUMAN_APPROVED")
            stored_evidence = evidence.strip()
        else:
            stored_evidence = evidence

        self.stage = new_stage
        if stored_evidence is not None:
            self.evidence.append(stored_evidence)
        self.audit.append({"stage": new_stage, "evidence": stored_evidence})
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "customer": self.customer,
            "problem": self.problem,
            "offer": self.offer,
            "stage": self.stage,
            "evidence": self.evidence,
            "value_note": self.value_note,
            "audit": self.audit,
        }
