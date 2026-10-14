"""Declarative proof gate registry for Electronic Brain.

The default definitions specify evidence requirements only. They do not imply
that collectors, authenticated external sources, or real-world evidence exist.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from .proof_gate_engine import ProofGateEngine


@dataclass(frozen=True)
class GateDefinition:
    gate_id: str
    required_proof_types: tuple[str, ...]
    max_age_seconds: int


DEFAULT_GATES = (
    GateDefinition("runtime_software", ("unit_test_report", "runtime_health"), 86400),
    GateDefinition("bitcoin_mining_live", ("pool_connection", "observed_hashrate", "accepted_share"), 900),
    GateDefinition("revenue_realized", ("provider_payout", "blockchain_confirmation"), 86400),
    GateDefinition("asic_gdsii", ("gdsii_artifact", "physical_design_report"), 604800),
    GateDefinition("foundry_acceptance", ("foundry_acceptance_document",), 2592000),
    GateDefinition("silicon_manufacture", ("manufacturing_confirmation",), 2592000),
    GateDefinition("silicon_test", ("silicon_test_report",), 2592000),
    GateDefinition("device_execution", ("device_heartbeat", "task_postcondition"), 300),
)


class ProofGateRegistry:
    """Look up declarative gate requirements and delegate decisions to the engine."""

    def __init__(self, definitions: Sequence[GateDefinition] = DEFAULT_GATES):
        self._definitions: dict[str, GateDefinition] = {}
        for definition in definitions:
            if not isinstance(definition, GateDefinition):
                raise TypeError("definitions must contain GateDefinition values")
            if not definition.gate_id.strip() or not definition.required_proof_types:
                raise ValueError("gate ID and required proof types are mandatory")
            if definition.gate_id in self._definitions:
                raise ValueError(f"duplicate gate ID: {definition.gate_id}")
            if definition.max_age_seconds < 0:
                raise ValueError(f"invalid freshness window for {definition.gate_id}")
            self._definitions[definition.gate_id] = definition

    def list_gates(self) -> list[dict[str, Any]]:
        return [
            {
                "gate_id": gate.gate_id,
                "required_proof_types": list(gate.required_proof_types),
                "max_age_seconds": gate.max_age_seconds,
            }
            for gate in self._definitions.values()
        ]

    def get(self, gate_id: str) -> GateDefinition | None:
        return self._definitions.get(gate_id)

    def evaluate(
        self,
        gate_id: str,
        evidence_records: Sequence[Mapping[str, Any]] | None,
        *,
        expected_commit_sha: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        definition = self.get(gate_id)
        if definition is None:
            return {
                "gate_id": gate_id,
                "status": "UNKNOWN",
                "reason": "UNKNOWN_GATE_ID",
                "accepted_evidence_ids": [],
                "rejected_evidence": [],
            }
        return ProofGateEngine.evaluate(
            gate_id=definition.gate_id,
            required_proof_types=definition.required_proof_types,
            evidence_records=evidence_records,
            expected_commit_sha=expected_commit_sha,
            max_age_seconds=definition.max_age_seconds,
            now=now,
        )
