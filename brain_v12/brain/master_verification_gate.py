"""Master verification gate for Brain execution results."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .execution_verifier import Evidence, ExecutionVerifier


@dataclass(frozen=True)
class GateResult:
    status: str
    verified: bool
    capability: str
    executor_id: str | None
    evidence: dict[str, Any]
    reason: str


class MasterVerificationGate:
    """Single final gate: VERIFIED_COMPLETED only when evidence is valid."""

    def __init__(self, verifier: ExecutionVerifier | None = None):
        self.verifier = verifier or ExecutionVerifier()

    def evaluate(self, capability: str, executor_id: str | None,
                 result: Any) -> GateResult:
        if not executor_id:
            return GateResult("FAILED", False, capability, None, {},
                               "NO_EXECUTOR")
        evidence: Evidence = self.verifier.verify(capability, executor_id, result)
        if not evidence.verified:
            return GateResult("FAILED", False, capability, executor_id,
                               asdict(evidence), "EVIDENCE_REJECTED")
        return GateResult("VERIFIED_COMPLETED", True, capability, executor_id,
                          asdict(evidence), "EVIDENCE_ACCEPTED")
