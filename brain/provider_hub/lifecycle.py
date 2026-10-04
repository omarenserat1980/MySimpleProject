"""Evidence-aware provider lifecycle and failover engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


LIFECYCLE = ("DISCOVERED", "CONFIGURED", "HEALTHY", "VERIFIED", "ACTIVE")
FAILOVER_STATES = {"DEGRADED", "FAILED", "UNAVAILABLE"}


@dataclass
class ProviderRecord:
    provider_id: str
    capability: str
    priority: int
    state: str = "DISCOVERED"
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def add_evidence(self, evidence_type: str, payload: dict[str, Any]) -> None:
        self.evidence.append({"type": evidence_type, "payload": payload})

    def promote(self, target: str) -> None:
        if target not in LIFECYCLE:
            raise ValueError(f"INVALID_STATE:{target}")
        current_index = LIFECYCLE.index(self.state)
        target_index = LIFECYCLE.index(target)
        if target_index > current_index + 1:
            raise ValueError("LIFECENCE_STEP_REQUIRED")
        if target in {"VERIFIED", "ACTIVE"} and not self.evidence:
            raise ValueError("EVIDENCE_REQUIRED_FOR_ACTIVATION")
        self.state = target


class FailoverEngine:
    def __init__(self, records: list[ProviderRecord]):
        self.records = records

    def select(self, capability: str) -> ProviderRecord:
        active = [
            r for r in self.records
            if r.capability == capability and r.state == "ACTIVE"
        ]
        if not active:
            raise RuntimeError(f"NO_ACTIVE_PROVIDER:{capability}")
        return sorted(active, key=lambda r: r.priority)[0]

    def failover(self, capability: str, failed_provider_id: str) -> ProviderRecord:
        candidates = [
            r for r in self.records
            if r.capability == capability
            and r.provider_id != failed_provider_id
            and r.state == "ACTIVE"
        ]
        if not candidates:
            raise RuntimeError(f"NO_FAILOVER_PROVIDER:{capability}")
        return sorted(candidates, key=lambda r: r.priority)[0]
