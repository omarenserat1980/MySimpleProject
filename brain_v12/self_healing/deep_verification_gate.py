"""Bridge Deep Execution results through the independent evidence gate."""

from __future__ import annotations

from typing import Any

from brain_v12.self_healing.deep_execution_evidence_gate import DeepEvidenceGate


class DeepVerificationGate:
    def __init__(self, state_dir: str = ".brain/state/deep") -> None:
        self.gate = DeepEvidenceGate(state_dir)

    def verify(self, state: dict[str, Any]) -> dict[str, Any]:
        return self.gate.evaluate(state)
