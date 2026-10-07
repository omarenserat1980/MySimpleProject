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

    def validate(self) -> None:
        if not self.mission_id or not self.task_id or not self.action or not self.executor:
            raise ValueError("execution_contract_identity_required")
        if self.timeout_seconds < 1:
            raise ValueError("execution_contract_timeout_invalid")
        if self.risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("execution_contract_risk_invalid")
        if self.risk in {"HIGH", "CRITICAL"} and not self.evidence_required:
            raise ValueError("high_risk_requires_evidence")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
