"""Synthetic customer orchestration for safe end-to-end Brain testing.
The customer requests outcomes; Brain/ChatGPT propose implementation. Execution is gated.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

SAFE_CAPS={"website","landing_page","software","student_project","cinematic_video","image_factory","media_engine","api","automation"}
DANGEROUS={"production_payment","production_publish","real_charge","destructive_delete"}

@dataclass
class Proposal:
    source: str
    summary: str
    scope: list[str]
    risks: list[str]
    acceptance: list[str]
    requires_approval: bool=True

@dataclass
class TestRun:
    run_id: str
    customer_id: str
    customer_type: str
    request: str
    status: str
    chatgpt_proposal: dict[str,Any]|None=None
    brain_proposal: dict[str,Any]|None=None
    unified_proposal: dict[str,Any]|None=None
    approved: bool=False
    evidence: list[dict[str,Any]]|None=None

class SyntheticCustomer:
    def __init__(self, evidence_store=None):
        self.evidence_store=evidence_store

    def discover(self, capabilities: dict[str,Any]) -> dict[str,Any]:
        names=set()
        for key in ("capabilities","agents","tools","engines"):
            value=capabilities.get(key,[])
            if isinstance(value,dict): names.update(value.keys())
            elif isinstance(value,list): names.update(str(x.get("id",x.get("name",x))) if isinstance(x,dict) else str(x) for x in value)
        return {"known":sorted(names),"test_safe":[x for x in sorted(names) if any(k in x.lower() for k in SAFE_CAPS)],
                "blocked":[x for x in sorted(names) if any(k in x.lower() for k in DANGEROUS)]}

    def start(self, customer_type:str, request:str)->TestRun:
        return TestRun(str(uuid4()),f"synthetic-client-{uuid4().hex[:12]}",customer_type,request,"PROPOSAL_PENDING",evidence=[])

    def merge_proposals(self, chatgpt:Proposal, brain:Proposal)->dict[str,Any]:
        scope=list(dict.fromkeys(chatgpt.scope+brain.scope))
        acceptance=list(dict.fromkeys(chatgpt.acceptance+brain.acceptance))
        risks=list(dict.fromkeys(chatgpt.risks+brain.risks))
        return {"summary":brain.summary or chatgpt.summary,"scope":scope,"acceptance":acceptance,
                "risks":risks,"sources":["CHATGPT","BRAIN"],"approval_required":True}

    def approve(self, run:TestRun, proposal:dict[str,Any])->TestRun:
        run.unified_proposal=proposal; run.approved=True; run.status="APPROVED_FOR_TEST_EXECUTION"
        run.evidence=run.evidence or []
        run.evidence.append({"event":"CUSTOMER_APPROVED","at":datetime.now(timezone.utc).isoformat()})
        return run

    def safety_gate(self, environment:str, payment_mode:str|None=None)->dict[str,Any]:
        safe=environment.upper() in {"TEST","SANDBOX"} and (payment_mode or "NONE").upper()!="PRODUCTION"
        return {"allowed":safe,"environment":environment,"payment_mode":payment_mode or "NONE",
                "reason":"OK" if safe else "PAYMENT_SAFETY_GATE_BLOCKED"}
