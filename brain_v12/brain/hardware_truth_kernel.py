from __future__ import annotations

"""Durable truth/transaction boundary for the Piece-First hardware graph.

This module deliberately uses compensating transactions across independent
in-memory managers. It never claims distributed atomicity; it guarantees that
partial local reservations are compensated when the next reservation fails.
"""

import json
import os
import time
from pathlib import Path
from typing import Any

from .piece_graph import (
    HardwareGraph, Piece, Connection, Capacity, CapacityOrigin,
    PieceState, TruthLevel, ConnectionType,
)
from .resource_fabric import ResourceFabric


class HardwareTruthKernel:
    def __init__(
        self,
        graph: HardwareGraph,
        resource_fabric: ResourceFabric | None = None,
        state_path: str | Path = ".brain/state/hardware_truth_kernel.json",
    ) -> None:
        self.graph = graph
        self.resource_fabric = resource_fabric
        self.path = Path(state_path)
        self.journal: list[dict[str, Any]] = []
        self._load()

    def _snapshot(self) -> dict[str, Any]:
        return self.graph.snapshot()

    def persist(self, event: str = "SNAPSHOT") -> dict[str, Any]:
        payload = {
            "schema": 1,
            "saved_at": time.time(),
            "event": event,
            "graph": self._snapshot(),
            "journal": self.journal[-500:],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
        return {"ok": True, "status": "PERSISTED", "path": str(self.path)}

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            graph = payload.get("graph") or {}
            self._restore_graph(graph)
            self.journal = list(payload.get("journal") or [])[-500:]
        except (OSError, ValueError, TypeError, KeyError):
            # Corrupt durable state must never be promoted to truth.
            self.journal.append({
                "ts": time.time(),
                "event": "PERSISTED_STATE_REJECTED",
            })

    def _restore_graph(self, snapshot: dict[str, Any]) -> None:
        for item in (snapshot.get("pieces") or {}).values():
            p = Piece(
                piece_id=item["piece_id"],
                piece_type=item["piece_type"],
                domain=item["domain"],
                provider_id=item["provider_id"],
                backend=item.get("backend"),
                parent_id=item.get("parent_id"),
                state=PieceState(item["state"]),
                truth=TruthLevel(item["truth"]),
                capabilities=set(item.get("capabilities") or []),
                identity=dict(item.get("identity") or {}),
                health=item.get("health", "UNKNOWN"),
                evidence_ids=list(item.get("evidence_ids") or []),
                fencing_epoch=int(item.get("fencing_epoch", 0)),
            )
            for name, raw in (item.get("capacities") or {}).items():
                origin = raw.get("origin")
                if isinstance(origin, str):
                    origin = CapacityOrigin(origin)
                p.add_capacity(Capacity(
                    name=name,
                    amount=float(raw["amount"]),
                    unit=raw["unit"],
                    origin=origin,
                    owner_piece_id=raw["owner_piece_id"],
                    allocatable=bool(raw.get("allocatable", True)),
                    metadata=dict(raw.get("metadata") or {}),
                ))
            self.graph.add_piece(p)

        for item in (snapshot.get("connections") or {}).values():
            c = Connection(
                connection_id=item["connection_id"],
                source_piece_id=item["source_piece_id"],
                target_piece_id=item["target_piece_id"],
                connection_type=ConnectionType(item["connection_type"]),
                provider_id=item["provider_id"],
                backend=item.get("backend"),
                state=PieceState(item["state"]),
                truth=TruthLevel(item["truth"]),
                direction=item.get("direction", "BIDIRECTIONAL"),
                latency=item.get("latency"),
                bandwidth=item.get("bandwidth"),
                protocol=item.get("protocol"),
                evidence_ids=list(item.get("evidence_ids") or []),
                fencing_epoch=int(item.get("fencing_epoch", 0)),
            )
            self.graph.add_connection(c)

    def record(self, event: str, **data: Any) -> None:
        self.journal.append({"ts": time.time(), "event": event, **data})
        self.journal = self.journal[-500:]

    def reserve_transaction(
        self,
        intent_id: str,
        piece_ids: list[str],
        connection_ids: list[str],
        *,
        resource_allocations: list[dict[str, Any]] | None = None,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        before = self._snapshot()
        graph_result = self.graph.reserve_graph(
            intent_id, piece_ids, connection_ids, ttl_seconds=ttl_seconds
        )
        if not graph_result.get("ok"):
            return graph_result

        resource_result = None
        if self.resource_fabric is not None and resource_allocations:
            resource_result = self.resource_fabric.reserve(
                intent_id, allocations=resource_allocations,
                ttl_seconds=ttl_seconds,
            )
            if not resource_result.get("ok"):
                # Compensating rollback of graph reservation.
                self.graph.release_graph(
                    graph_result["reservation"]["reservation_id"]
                )
                self.record(
                    "TRANSACTION_ABORTED",
                    intent_id=intent_id,
                    reason=resource_result.get("status"),
                )
                return {
                    "ok": False,
                    "status": "TRANSACTION_ROLLED_BACK",
                    "graph": graph_result,
                    "resource": resource_result,
                }

        self.record(
            "TRANSACTION_RESERVED",
            intent_id=intent_id,
            graph_reservation=graph_result["reservation"]["reservation_id"],
            resource_reservation=(resource_result or {}).get("reservation", {}).get("reservation_id"),
        )
        self.persist("TRANSACTION_RESERVED")
        return {
            "ok": True,
            "status": "RESERVED",
            "graph": graph_result["reservation"],
            "resource": (resource_result or {}).get("reservation"),
            "rollback_snapshot": before,
        }

    def reconcile(
        self,
        piece_id: str,
        *,
        observed_state: PieceState,
        observed_truth: TruthLevel,
        evidence_ids: list[str],
        observed_at: float | None = None,
    ) -> dict[str, Any]:
        observed_at = time.time() if observed_at is None else observed_at
        piece = self.graph.pieces.get(piece_id)
        if piece is None:
            return {"ok": False, "status": "PIECE_NOT_FOUND"}

        if observed_at < float(piece.metadata.get("last_observed_at", 0)):
            return {"ok": False, "status": "STALE_OBSERVATION"}

        # Do not allow an observation to silently upgrade beyond VERIFIED.
        if observed_truth in {TruthLevel.VERIFIED, TruthLevel.ATTESTED} and not evidence_ids:
            return {"ok": False, "status": "EVIDENCE_REQUIRED_FOR_TRUTH_PROMOTION"}

        old_state, old_truth = piece.state, piece.truth
        piece.state = observed_state
        piece.truth = observed_truth
        piece.evidence_ids = list(evidence_ids)
        piece.metadata["last_observed_at"] = observed_at
        self.record(
            "PIECE_RECONCILED",
            piece_id=piece_id,
            old_state=old_state.value,
            new_state=observed_state.value,
            old_truth=old_truth.value,
            new_truth=observed_truth.value,
            evidence_ids=list(evidence_ids),
            observed_at=observed_at,
        )
        self.persist("PIECE_RECONCILED")
        return {
            "ok": True,
            "status": "RECONCILED",
            "piece": self.graph.piece_public(piece_id),
        }

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "status": "READY",
            "persistent": self.path.exists(),
            "state_path": str(self.path),
            "journal_count": len(self.journal),
            "graph": self.graph.inspect(),
        }
