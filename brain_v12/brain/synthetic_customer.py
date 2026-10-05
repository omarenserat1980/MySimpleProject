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


@dataclass(frozen=True)
class SyntheticExecutiveProfile:
    title: str = "CEO / General Manager"
    industries: tuple[str, ...] = (
        "software", "finance", "marketing", "sales", "social_media",
        "media", "cinema", "ecommerce", "education", "operations",
        "product", "strategy", "customer_success", "legal_compliance",
        "security", "data_ai", "hr", "procurement",
    )
    expertise: tuple[str, ...] = (
        "software_engineering", "architecture", "qa", "devops", "ai",
        "financial_planning", "unit_economics", "budgeting", "pricing",
        "sales", "branding", "seo", "content_marketing", "social_media",
        "performance_marketing", "analytics", "product_management",
        "operations", "risk_management", "business_strategy",
    )
    scale_target: str = "millions_of_logical_customer_scenarios"
    service_model: str = "long_running_advisory_and_acceptance"

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "industries": list(self.industries),
            "expertise": list(self.expertise),
            "scale_target": self.scale_target,
            "service_model": self.service_model,
        }


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
                 brain_advisor: Callable | None = None, executor: Callable | None = None,
                 repair_executor: Callable | None = None,
                 feedback_executor: Callable | None = None,
                 executive_profile: SyntheticExecutiveProfile | None = None,
                 max_repair_attempts: int = 1):
        self.evidence_store = evidence_store
        self.chatgpt_advisor = chatgpt_advisor
        self.brain_advisor = brain_advisor
        self.executor = executor
        self.repair_executor = repair_executor
        self.feedback_executor = feedback_executor
        self.max_repair_attempts = max(0, min(int(max_repair_attempts), 3))
        self.runs: dict[str, TestRun] = {}
        self.executive_profile = executive_profile or SyntheticExecutiveProfile()

    def discover(self, capabilities: dict[str, Any]) -> dict[str, Any]:
        names = set()
        for key in ("capabilities", "agents", "tools", "engines"):
            value = capabilities.get(key, [])
            if isinstance(value, dict): names.update(value.keys())
            elif isinstance(value, list):
                names.update(str(x.get("id", x.get("name", x))) if isinstance(x, dict) else str(x) for x in value)
        return {"known": sorted(names), "executive_profile": self.executive_profile.as_dict()}

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
        if not run.approved:
            raise ValueError("CUSTOMER_APPROVAL_REQUIRED")
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
        attempts = []
        try:
            for attempt in range(self.max_repair_attempts + 1):
                result = self.executor(run.request, run.customer_type, run.run_id)
                ok = self._execution_verified(result)
                attempts.append({"attempt": attempt + 1, "verified": ok, "result": result})
                if ok:
                    run.execution = {"ok": True, "gate": gate, "result": result, "attempts": attempts}
                    if self.evidence_store:
                        evidence = self.evidence_store.append(run.run_id, "synthetic-customer-execution", run.execution, "synthetic-customer")
                        verification = self.evidence_store.verify_hash(evidence["evidence_id"])
                        run.execution.update({"evidence_id": evidence["evidence_id"], "evidence_sha256": evidence["sha256"], "evidence_verified": verification["ok"]})
                        ok = verification["ok"]
                    run.status = "VERIFIED" if ok else "EXECUTION_FAILED"
                    break
                if attempt >= self.max_repair_attempts or not self.repair_executor:
                    run.execution = {"ok": False, "gate": gate, "result": result, "attempts": attempts}
                    run.status = "EXECUTION_FAILED"
                    break
                gap = self.repair_executor(run.request, result, run.customer_type, run.run_id)
                run.evidence = run.evidence or []
                run.evidence.append({"event": "BRAIN_GAP_REPAIR_ATTEMPT", "attempt": attempt + 1, "gap": gap, "at": datetime.now(timezone.utc).isoformat()})
                if not isinstance(gap, dict) or gap.get("ok") is not True:
                    run.execution = {"ok": False, "gate": gate, "result": result, "repair": gap, "attempts": attempts}
                    run.status = "EXECUTION_FAILED"
                    break
            run.evidence = run.evidence or []
            run.evidence.append({"event": "EXECUTION_VERIFIED" if run.status == "VERIFIED" else "EXECUTION_FAILED", "at": datetime.now(timezone.utc).isoformat(), "result": run.execution})
        except Exception as exc:
            run.status, run.execution = "EXECUTION_FAILED", {"ok": False, "gate": gate, "error": str(exc)[:1000], "attempts": attempts}
            run.evidence = run.evidence or []
            run.evidence.append({"event": "EXECUTION_FAILED", "error": str(exc)[:1000]})
        return run

    def review(self, run: TestRun, accepted: bool, feedback: str = "") -> TestRun:
        if run.status not in {"VERIFIED", "EXECUTION_FAILED"}:
            raise ValueError("CUSTOMER_REVIEW_NOT_READY")
        run.evidence = run.evidence or []
        run.evidence.append({
            "event": "CUSTOMER_ACCEPTANCE" if accepted else "CUSTOMER_REVISION_REQUESTED",
            "feedback": feedback,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        if accepted:
            run.status = "ACCEPTED"
        else:
            run.status = "REVISION_REQUESTED"
            if self.feedback_executor:
                feedback_result = self.feedback_executor(run.request, feedback, run.customer_type, run.run_id)
                run.evidence.append({"event": "CUSTOMER_FEEDBACK_FORWARDED_TO_BRAIN", "feedback": feedback, "feedback_result": feedback_result, "at": datetime.now(timezone.utc).isoformat()})
        return run

    def revise(self, run: TestRun, feedback: str) -> TestRun:
        if run.status != "REVISION_REQUESTED":
            raise ValueError("REVISION_NOT_REQUESTED")
        run.approved = False
        run.status = "WAITING_CUSTOMER_APPROVAL"
        run.request = f"{run.request}\nCustomer revision feedback: {feedback}"
        run.evidence = run.evidence or []
        run.evidence.append({
            "event": "REVISION_CAPTURED",
            "feedback": feedback,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        return run

    def deliver(self, run: TestRun) -> TestRun:
        if run.status != "ACCEPTED":
            raise ValueError("CUSTOMER_ACCEPTANCE_REQUIRED")
        run.status = "DELIVERED"
        run.evidence = run.evidence or []
        run.evidence.append({"event": "DELIVERED", "at": datetime.now(timezone.utc).isoformat()})
        return run

    @staticmethod
    def safety_gate(environment: str, payment_mode: str | None = None) -> dict[str, Any]:
        safe = environment.upper() in {"TEST", "SANDBOX"} and (payment_mode or "NONE").upper() != "PRODUCTION"
        return {"allowed": safe, "environment": environment, "payment_mode": payment_mode or "NONE",
                "reason": "OK" if safe else "PAYMENT_SAFETY_GATE_BLOCKED"}
"