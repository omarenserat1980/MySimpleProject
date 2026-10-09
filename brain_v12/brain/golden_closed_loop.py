from __future__ import annotations

"""BRAIN Golden Closed Loop: fail-closed orchestration with sealed evidence."""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

SCHEMA = "brain.golden-closed-loop.v1"
SUCCESS = "SUCCESS"
REPAIR = "REPAIR"
CLOSED = "CLOSED"


@dataclass(frozen=True)
class GoldenDecision:
    status: str
    phase: str
    verified: bool
    reasons: tuple[str, ...]
    evidence_sha256: str
    closed: bool
    repair_required: bool
    decided_at: float


class TruthGate:
    """Only authority allowed to convert evidence into SUCCESS."""

    REQUIRED = (
        "goal_verified",
        "evidence_verified",
        "execution_verified",
        "independent_verification",
        "cost_gate_ok",
    )

    def evaluate(self, evidence: Mapping[str, Any]) -> GoldenDecision:
        reasons: list[str] = []
        for key in self.REQUIRED:
            if evidence.get(key) is not True:
                reasons.append(f"TRUTH_GATE_{key.upper()}_FAILED")
        if evidence.get("rollback_ready") is not True:
            reasons.append("TRUTH_GATE_ROLLBACK_NOT_READY")
        if evidence.get("evidence_sealed") is True:
            reasons.append("TRUTH_GATE_EVIDENCE_ALREADY_SEALED")
        payload = json.dumps(dict(evidence), sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(payload).hexdigest()
        verified = not reasons
        return GoldenDecision(
            status=SUCCESS if verified else REPAIR,
            phase="TRUTH_GATE",
            verified=verified,
            reasons=tuple(reasons),
            evidence_sha256=digest,
            closed=False,
            repair_required=not verified,
            decided_at=time.time(),
        )


class GoldenClosedLoop:
    """One closed cycle: prove -> decide -> verify -> seal, else repair."""

    def __init__(self, *, truth_gate: TruthGate | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self.truth_gate = truth_gate or TruthGate()
        self.clock = clock

    def run(self, evidence: Mapping[str, Any]) -> dict[str, Any]:
        decision = self.truth_gate.evaluate(evidence)
        record = {
            "schema": SCHEMA,
            "status": decision.status,
            "phase": decision.phase,
            "verified": decision.verified,
            "reasons": list(decision.reasons),
            "evidence_sha256": decision.evidence_sha256,
            "repair_required": decision.repair_required,
            "closed": False,
            "decided_at": decision.decided_at,
        }
        if not decision.verified:
            record["next_action"] = REPAIR
            return record

        sealed = dict(evidence)
        sealed["evidence_sealed"] = True
        sealed["sealed_at"] = self.clock()
        sealed_payload = json.dumps(sealed, sort_keys=True, separators=(",", ":")).encode()
        record.update({
            "status": CLOSED,
            "phase": "SEALED",
            "closed": True,
            "seal_sha256": hashlib.sha256(sealed_payload).hexdigest(),
            "next_action": "NONE",
        })
        return record
