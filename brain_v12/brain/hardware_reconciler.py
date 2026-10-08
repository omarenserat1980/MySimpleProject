from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
import time

from .piece_graph import HardwareGraph, PieceState, TruthLevel


class DriftKind(str, Enum):
    NONE = "NONE"
    CAPACITY = "CAPACITY_DRIFT"
    IDENTITY = "IDENTITY_DRIFT"
    TOPOLOGY = "TOPOLOGY_DRIFT"
    HEALTH = "HEALTH_DRIFT"
    ATTACHMENT = "ATTACHMENT_DRIFT"
    STALE = "STALE"


@dataclass(frozen=True)
class Observation:
    component_id: str
    identity: str | None
    capacity: dict[str, Any]
    health: str
    attached: bool
    state: PieceState | None = None
    truth: TruthLevel = TruthLevel.OBSERVED
    evidence_ids: tuple[str, ...] = ()


class HardwareReconciler:
    """Evidence-aware reconciliation between desired and provider-observed state."""

    def __init__(self, stale_after_seconds: float = 120.0,
                 graph: HardwareGraph | None = None,
                 evidence_store: Any | None = None):
        self.stale_after_seconds = float(stale_after_seconds)
        self.graph = graph
        self.evidence_store = evidence_store

    def compare(self, desired: dict[str, Any], observed: Observation | None,
                observed_at: float | None = None, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        if observed is None or observed_at is None or now - observed_at > self.stale_after_seconds:
            return {"ok": False, "status": "STALE", "drift": DriftKind.STALE.value}
        if desired.get("identity") and observed.identity and desired["identity"] != observed.identity:
            return {"ok": False, "status": "QUARANTINE", "drift": DriftKind.IDENTITY.value}
        if desired.get("capacity") != observed.capacity:
            return {"ok": False, "status": "RECONCILE", "drift": DriftKind.CAPACITY.value,
                    "desired": desired.get("capacity"), "observed": observed.capacity}
        if desired.get("health") and desired["health"] != observed.health:
            return {"ok": False, "status": "RECONCILE", "drift": DriftKind.HEALTH.value}
        if bool(desired.get("attached")) != observed.attached:
            return {"ok": False, "status": "RECONCILE", "drift": DriftKind.ATTACHMENT.value}
        return {"ok": True, "status": "IN_SYNC", "drift": DriftKind.NONE.value}

    def reconcile_piece(self, observation: Observation, observed_at: float | None = None,
                        now: float | None = None) -> dict[str, Any]:
        if self.graph is None:
            return {"ok": False, "status": "GRAPH_NOT_CONFIGURED"}
        now = time.time() if now is None else now
        observed_at = now if observed_at is None else observed_at
        piece = self.graph.pieces.get(observation.component_id)
        if piece is None:
            return {"ok": False, "status": "PIECE_NOT_FOUND"}
        last = float(piece.metadata.get("last_observed_at", 0.0))
        if observed_at < last:
            return {"ok": False, "status": "STALE_OBSERVATION"}
        if observation.truth in {TruthLevel.VERIFIED, TruthLevel.ATTESTED} and not observation.evidence_ids:
            return {"ok": False, "status": "EVIDENCE_REQUIRED"}
        if observation.identity and piece.identity:
            for key, value in observation.identity.items():
                if key in piece.identity and piece.identity[key] != value:
                    piece.state = PieceState.QUARANTINED
                    piece.health = "CONFLICT"
                    return {"ok": False, "status": "IDENTITY_CONFLICT", "quarantined": True}
        piece.metadata["last_observed_at"] = observed_at
        piece.evidence_ids = list(observation.evidence_ids)
        piece.health = observation.health
        if observation.state is not None:
            piece.state = observation.state
        piece.truth = observation.truth
        if observation.identity:
            piece.identity.update(observation.identity)
        return {"ok": True, "status": "RECONCILED", "piece_id": piece.piece_id,
                "observed_at": observed_at, "evidence_ids": list(observation.evidence_ids)}

    def reconcile_plan(self, comparison: dict[str, Any]) -> dict[str, Any]:
        drift = comparison.get("drift", DriftKind.NONE.value)
        actions = {
            DriftKind.NONE.value: [],
            DriftKind.STALE.value: ["MARK_STALE", "STOP_NEW_ADMISSIONS"],
            DriftKind.IDENTITY.value: ["QUARANTINE", "FENCE", "REQUEST_REATTESTATION"],
            DriftKind.CAPACITY.value: ["REFRESH_RESOURCE_CAPACITY", "VERIFY"],
            DriftKind.HEALTH.value: ["MARK_DEGRADED", "VERIFY"],
            DriftKind.ATTACHMENT.value: ["RECONCILE_ATTACHMENT", "VERIFY"],
            DriftKind.TOPOLOGY.value: ["REBUILD_AFFECTED_EDGES", "VERIFY"],
        }.get(drift, ["QUARANTINE"])
        return {"ok": comparison.get("status") != "QUARANTINE",
                "status": "ACTION_REQUIRED" if actions else "IN_SYNC",
                "actions": actions, "drift": drift}
