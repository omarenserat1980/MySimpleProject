"""Explicit execution contract shared by planner, executor and verifier."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class ExecutionContract:
    mission_id: str
    task_id: str
    action: str
    executor: str
    preconditions: tuple[str, ...] = ()
    expected_results: tuple[str, ...] = ()
    timeout_seconds: int = 60
    evidence_required: bool = True
    risk: str = "LOW"
    idempotency_key: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    leadership_fencing_token: int | None = None
    authority_policy_version: str = "authority-policy-v1"
    authority_decision: str = "DENIED"

    def validate(self) -> None:
        if not self.mission_id or not self.task_id or not self.action or not self.executor:
            raise ValueError("execution_contract_identity_required")
        if self.timeout_seconds < 1:
            raise ValueError("execution_contract_timeout_invalid")
        if self.risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("execution_contract_risk_invalid")
        if self.risk in {"HIGH", "CRITICAL"} and not self.evidence_required:
            raise ValueError("high_risk_requires_evidence")
        if not self.authority_policy_version:
            raise ValueError("execution_contract_authority_policy_required")
        if self.authority_decision not in {"AUTHORIZED", "DENIED"}:
            raise ValueError("execution_contract_authority_decision_invalid")
        if self.risk in {"HIGH", "CRITICAL"} and self.authority_decision != "AUTHORIZED":
            raise ValueError("high_risk_requires_authorized_authority_decision")
        if self.leadership_fencing_token is not None:
            if (not isinstance(self.leadership_fencing_token, int)
                    or isinstance(self.leadership_fencing_token, bool)
                    or self.leadership_fencing_token < 1):
                raise ValueError("execution_contract_fencing_token_invalid")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
