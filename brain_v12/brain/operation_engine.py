from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4


@dataclass(frozen=True)
class OperationSpec:
    operation_type: str
    objective: str
    auto_prompt: str
    tools: tuple[str, ...] = ()
    human_gate: bool = False
    success_conditions: tuple[str, ...] = ()
    retry_limit: int = 2


class OperationEngine:
    """Deterministic operation registry: prompt -> policy -> executor -> verification -> audit."""

    BASE = (
        "Operate autonomously within declared permissions. "
        "Inspect before changing. Preserve legacy. "
        "Do not invent evidence or claim success without verification. "
        "On failure, diagnose before retrying. "
        "Stop at a genuine HUMAN_GATE for secrets, identity, payments, CAPTCHA, OTP, "
        "destructive production changes, or missing authorization."
    )

    TEMPLATES = {
        "CODE_CHANGE": "Inspect the requested code area, plan the smallest safe change, implement it, test it, verify it, document it, and commit only after evidence.",
        "GITHUB": "Inspect repository state, compare before changing, apply the requested repository operation, verify the resulting commit/files/actions, and report evidence.",
        "RENDER": "Inspect service, deployment, logs, and health. Diagnose the failure class before changing anything. Preserve the existing service and avoid creating a new service unless explicitly authorized.",
        "TEST": "Discover the relevant test surface, run deterministic tests, classify failures, repair only when permitted, rerun, and retain evidence.",
        "MONITORING": "Inspect the alert and correlated runtime evidence, deduplicate the incident, attempt a safe recovery when permitted, verify health, and audit the result.",
        "REVENUE": "Discover only evidence-backed opportunities, qualify them, prepare the smallest lawful action, verify delivery/payment evidence, and never fabricate revenue.",
        "YOUTUBE": "Validate media and metadata, check authorization, perform the permitted publishing step, verify the remote result, and audit it.",
        "DEVICE": "Verify device identity and authorization, dispatch only an allowed task, wait for the result, verify it, and record success or failure.",
        "BROWSER": "Use only the declared browser provider and permitted actions. Never bypass CAPTCHA, KYC, OTP, identity checks, or account security controls.",
        "BACKUP": "Create a restorable backup before mutation, verify backup integrity, then allow the protected operation to continue.",
    }

    def __init__(self, store):
        self.store = store
        self.executors: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register_executor(self, operation_type: str, executor: Callable[[dict[str, Any]], Any]) -> None:
        self.executors[operation_type.upper()] = executor

    def build(self, operation_type: str, objective: str, tools: list[str] | None = None,
              human_gate: bool = False, success_conditions: list[str] | None = None,
              retry_limit: int = 2) -> dict[str, Any]:
        kind = operation_type.upper()
        instruction = self.TEMPLATES.get(kind, "Inspect, plan, execute within permissions, test, verify, document, and audit.")
        prompt = f"{self.BASE} Operation: {kind}. Objective: {objective}. {instruction}"
        spec = OperationSpec(kind, objective, prompt, tuple(tools or ()), human_gate,
                             tuple(success_conditions or ("Execution completed and independently verified.",)),
                             max(0, min(retry_limit, 5)))
        operation = {
            "operation_id": f"op-{uuid4().hex}",
            **asdict(spec),
            "tools": list(spec.tools),
            "success_conditions": list(spec.success_conditions),
            "status": "AWAITING_APPROVAL" if human_gate else "READY",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.store.event("OPERATION_CREATED", operation)
        return operation

    def run(self, operation: dict[str, Any]) -> dict[str, Any]:
        op_id = operation["operation_id"]
        kind = operation["operation_type"].upper()
        if operation.get("human_gate"):
            result = {**operation, "status": "AWAITING_APPROVAL", "result": None}
            self.store.event("OPERATION_HUMAN_GATE", {"operation_id": op_id, "operation_type": kind})
            return result
        executor = self.executors.get(kind)
        if executor is None:
            result = {**operation, "status": "BLOCKED", "error": "NO_EXECUTOR_REGISTERED"}
            self.store.event("OPERATION_BLOCKED", {"operation_id": op_id, "reason": result["error"]})
            return result
        attempts = 0
        last_error = None
        while attempts <= int(operation.get("retry_limit", 2)):
            attempts += 1
            self.store.event("OPERATION_STARTED", {"operation_id": op_id, "attempt": attempts})
            try:
                value = executor(operation)
                if isinstance(value, dict) and value.get("verified") is False:
                    raise RuntimeError("EXECUTION_NOT_VERIFIED")
                result = {**operation, "status": "SUCCESS", "attempts": attempts, "result": value}
                self.store.event("OPERATION_VERIFIED", {"operation_id": op_id, "attempts": attempts})
                return result
            except Exception as exc:
                last_error = str(exc)
                self.store.event("OPERATION_FAILED", {"operation_id": op_id, "attempt": attempts, "error": last_error[:1000]})
        return {**operation, "status": "FAILED", "attempts": attempts, "error": last_error}
