""""Autonomous synthetic customer: realistic requests, dual proposals, approval and safety gates."""
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
    execution: dict[str, Any] | None = None


class SyntheticCustomer:
    def __init__(self, evidence_store=None, chatgpt_advisor: Callable | None = None,
                 brain_advisor: Callable | None = None, executor: Callable | None = None):
        self.evidence_store = evidence_store
        self.chatgpt_advisor = chatgpt_advisor
        self.brain_advisor = brain_advisor
        self.executor = executor
        self.runs: dict[str, TestRun] = {}

    def discover(self, capabilities: dict[str, Any]) -> dict[str, Any]:
        names = set()
        for key in ("capabilities", "agents", "tools", "engines"):
            value = capabilities.get(key, [])
            if isinstance(value, dict): names.update(value.keys())
            elif isinstance(value, list):
                names.update(str(x.get("id", x.get("name", x))) if isinstance(x, dict) else str(x) for x in value)
        return {"known": sorted(names)}

    def start(self, customer_type: str, request: str) -> TestRun:
        run = TestRun(str(uuid4()), f"synthetic-client-{uuid4().hex[:12]}", customer_type,
                      request, "PROPOSAL_PENDING", evidence=[])
        self.runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> TestRun:
        if run_id not in self.runs: raise KeyError("SYNTHETIC_RUN_NOT_FOUND")
        return self.runs[run_id]

    @staticmethod
    def _advisor_dict(raw: Any) -> dict[str, Any]:
        return raw if isinstance(raw, dict) else {"reply": str(raw)}

    def generate_proposals(self, run: TestRun, capabilities: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.chatgpt_advisor:
            raw = self._advisor_dict(self.chatgpt_advisor(run.request))
        else:
            raw = {}
        chat = Proposal("CHATGPT", str(raw.get("summary", raw.get("reply", "Independent product/UX proposal generated from the customer request."))),
                        list(raw.get("scope", ["requirements", "ux", "acceptance"])),
                        list(raw.get("risks", ["scope ambiguity"])),
                        list(raw.get("acceptance", ["requested outcome verified"])))
        if self.brain_advisor:
            raw = self._advisor_dict(self.brain_advisor(run.request, capabilities or {}))
        else:
            raw = {}
        steps = raw.get("steps", [])
        brain = Proposal("BRAIN", str(raw.get("summary") or raw.get("objective") or "Execution proposal based only on discovered Brain capabilities."),
                         list(raw.get("scope", steps or ["discover_capabilities", "test_execution", "verification"])),
                         list(raw.get("risks", [])),
                         list(raw.get("acceptance", ["execution completed", "result verified"])))
        run.chatgpt_proposal, run.brain_proposal = chat.__dict__, brain.__dict__
        run.unified_proposal = self.merge_proposals(chat, brain)
        run.status = "WAITING_CUSTOMER_APPROVAL"
        return {"chatgpt": run.chatgpt_proposal, "brain": run.brain_proposal, "unified": run.unified_proposal}

    def merge_proposals(self, chatgpt: Proposal, brain: Proposal) -> dict[str, Any]:
        return {"summary": brain.summary or chatgpt.summary,
                "scope": list(dict.fromkeys(chatgpt.scope + brain.scope)),
                "acceptance": list(dict.fromkeys(chatgpt.acceptance + brain.acceptance)),
                "risks": list(dict.fromkeys(chatgpt.risks + brain.risks)),
                "sources": ["CHATGPT", "BRAIN"], "approval_required": True}

    def approve(self, run: TestRun) -> TestRun:
        if not run.unified_proposal: raise ValueError("PROPOSAL_REQUIRED_BEFORE_APPROVAL")
        run.approved, run.status = True, "APPROVED_FOR_TEST_EXECUTION"
        run.evidence = run.evidence or []
        run.evidence.append({"event": "CUSTOMER_APPROVED", "at": datetime.now(timezone.utc).isoformat()})
        return run

    @staticmethod
    def _execution_verified(result: Any) -> bool:
        if not isinstance(result, dict) or not bool(result.get("ok")):
            return False
        cognitive = result.get("cognitive")
        if isinstance(cognitive, dict):
            execution = cognitive.get("execution", {})
            verification = cognitive.get("verification", {})
            return execution.get("status") == "COMPLETED" and verification.get("status") == "VERIFIED"
        return bool(result.get("verified") is True)

    def execute(self, run: TestRun, environment: str = "TEST", payment_mode: str = "NONE") -> TestRun:
        if not run.approved: raise ValueError("CUSTOMER_APPROVAL_REQUIRED")
        gate = self.safety_gate(environment, payment_mode)
        if not gate["allowed"]:
            run.status, run.execution = "PAYMENT_SAFETY_GATE_BLOCKED", {"ok": False, "gate": gate}
            run.evidence = run.evidence or []
            run.evidence.append({"event": "PAYMENT_SAFETY_GATE_BLOCKED", "gate": gate})
            return run
        if not self.executor:
            run.status, run.execution = "EXECUTION_UNAVAILABLE", {"ok": False, "status": "EXECUTION_UNAVAILABLE", "gate": gate}
            return run
        run.status = "EXECUTING"
        try:
            result = self.executor(run.request, run.customer_type, run.run_id)
            ok = self._execution_verified(result)
            run.execution = {"ok": ok, "gate": gate, "result": result}
            if ok and self.evidence_store:
                evidence = self.evidence_store.append(run.run_id, "synthetic-customer-execution", run.execution, "synthetic-customer")
                verification = self.evidence_store.verify_hash(evidence["evidence_id"])
                run.execution.update({"evidence_id": evidence["evidence_id"], "evidence_sha256": evidence["sha256"], "evidence_verified": verification["ok"]})
                ok = ok and verification["ok"]
            run.status = "VERIFIED" if ok else "EXECUTION_FAILED"
            run.evidence = run.evidence or []
            run.evidence.append({"event": "EXECUTION_VERIFIED" if ok else "EXECUTION_FAILED", "at": datetime.now(timezone.utc).isoformat(), "result": result})
        except Exception as exc:
            run.status, run.execution = "EXECUTION_FAILED", {"ok": False, "gate": gate, "error": str(exc)[:1000]}
            run.evidence = run.evidence or []
            run.evidence.append({"event": "EXECUTION_FAILED", "error": str(exc)[:1000]})
        return run

    @staticmethod
    def safety_gate(environment: str, payment_mode: str | None = None) -> dict[str, Any]:
        safe = environment.upper() in {"TEST", "SANDBOX"} and (payment_mode or "NONE").upper() != "PRODUCTION"
        return {"allowed": safe, "environment": environment, "payment_mode": payment_mode or "NONE",
                "reason": "OK" if safe else "PAYMENT_SAFETY_GATE_BLOCKED"}
"