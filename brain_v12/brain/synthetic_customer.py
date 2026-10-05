"""Autonomous synthetic customer: realistic requests, dual proposals, approval and safety gates."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Callable

@dataclass
class Proposal:
    source: str
    summary: str
    scope: list[str]
    risks: list[str]
    acceptance: list[str]
    requires_approval: bool = True

@dataclass
class TestRun:
    run_id: str
    customer_id: str
    customer_type: str
    request: str
    status: str
    chatgpt_proposal: dict[str, Any] | None = None
    brain_proposal: dict[str, Any] | None = None
    unified_proposal: dict[str, Any] | None = None
    approved: bool = False
    evidence: list[dict[str, Any]] | None = None

class SyntheticCustomer:
    def __init__(self, evidence_store=None, chatgpt_advisor: Callable | None = None, brain_advisor: Callable | None = None):
        self.evidence_store = evidence_store
        self.chatgpt_advisor = chatgpt_advisor
        self.brain_advisor = brain_advisor
        self.runs: dict[str, TestRun] = {}

    def discover(self, capabilities: dict[str, Any]) -> dict[str, Any]:
        names = set()
        for key in ("capabilities", "agents", "tools", "engines"):
            value = capabilities.get(key, [])
            if isinstance(value, dict):
                names.update(value.keys())
            elif isinstance(value, list):
                names.update(str(x.get("id", x.get("name", x))) if isinstance(x, dict) else str(x) for x in value)
        return {"known": sorted(names)}

    def start(self, customer_type: str, request: str) -> TestRun:
        run = TestRun(str(uuid4()), f"synthetic-client-{uuid4().hex[:12]}", customer_type, request, "PROPOSAL_PENDING", evidence=[])
        self.runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> TestRun:
        if run_id not in self.runs:
            raise KeyError("SYNTHETIC_RUN_NOT_FOUND")
        return self.runs[run_id]

    def generate_proposals(self, run: TestRun, capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.chatgpt_advisor:
            raw = self.chatgpt_advisor(run.request)
            chat = Proposal("CHATGPT", str(raw.get("summary", raw.get("reply", ""))), raw.get("scope", []), raw.get("risks", []), raw.get("acceptance", []))
        else:
            chat = Proposal("CHATGPT", "Independent product/UX proposal generated from the customer request.", ["requirements", "ux", "acceptance"], ["scope ambiguity"], ["requested outcome verified"])
        if self.brain_advisor:
            raw = self.brain_advisor(run.request, capabilities or {})
            brain = Proposal("BRAIN", str(raw.get("summary", "")), raw.get("scope", []), raw.get("risks", []), raw.get("acceptance", []))
        else:
            brain = Proposal("BRAIN", "Execution proposal based only on discovered Brain capabilities.", ["discover_capabilities", "test_execution", "verification"], [], ["artifact verified"])
        run.chatgpt_proposal = chat.__dict__
        run.brain_proposal = brain.__dict__
        run.unified_proposal = self.merge_proposals(chat, brain)
        run.status = "WAITING_CUSTOMER_APPROVAL"
        return {"chatgpt": chat.__dict__, "brain": brain.__dict__, "unified": run.unified_proposal}

    def merge_proposals(self, chatgpt: Proposal, brain: Proposal) -> dict[str, Any]:
        return {"summary": brain.summary or chatgpt.summary,
                "scope": list(dict.fromkeys(chatgpt.scope + brain.scope)),
                "acceptance": list(dict.fromkeys(chatgpt.acceptance + brain.acceptance)),
                "risks": list(dict.fromkeys(chatgpt.risks + brain.risks)),
                "sources": ["CHATGPT", "BRAIN"], "approval_required": True}

    def approve(self, run: TestRun) -> TestRun:
        if not run.unified_proposal:
            raise ValueError("PROPOSAL_REQUIRED_BEFORE_APPROVAL")
        run.approved = True
        run.status = "APPROVED_FOR_TEST_EXECUTION"
        run.evidence = run.evidence or []
        run.evidence.append({"event": "CUSTOMER_APPROVED", "at": datetime.now(timezone.utc).isoformat()})
        return run

    def safety_gate(self, environment: str, payment_mode: str | None = None) -> dict[str, Any]:
        safe = environment.upper() in {"TEST", "SANDBOX"} and (payment_mode or "NONE").upper() != "PRODUCTION"
        return {"allowed": safe, "environment": environment, "payment_mode": payment_mode or "NONE",
                "reason": "OK" if safe else "PAYMENT_SAFETY_GATE_BLOCKED"}
