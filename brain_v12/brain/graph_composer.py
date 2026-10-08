from __future__ import annotations

"""Graph composition and piece replacement control-plane.

This layer treats every hardware-like object as an independently replaceable
piece. It never invents physical capacity: VERIFIED/ATTESTED truth must come
from evidence or an explicitly supplied non-physical simulation mode.
"""

from dataclasses import dataclass
from copy import deepcopy
from typing import Any

from .piece_graph import (
    HardwareGraph,
    Piece,
    PieceRequirement,
    Connection,
    ConnectionRequirement,
    PieceState,
    TruthLevel,
    ConnectionType,
)


@dataclass(frozen=True)
class ReplacementPlan:
    intent_id: str
    old_piece_id: str
    new_piece_id: str
    preserved_piece_ids: tuple[str, ...]
    detached_connection_ids: tuple[str, ...]
    planned_connection_ids: tuple[str, ...]
    status: str
    blockers: tuple[str, ...] = ()

    def public(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "old_piece_id": self.old_piece_id,
            "new_piece_id": self.new_piece_id,
            "preserved_piece_ids": list(self.preserved_piece_ids),
            "detached_connection_ids": list(self.detached_connection_ids),
            "planned_connection_ids": list(self.planned_connection_ids),
            "status": self.status,
            "blockers": list(self.blockers),
        }


class GraphComposer:
    """Constraint-aware planner over independent pieces and connections."""

    def __init__(self, graph: HardwareGraph, evidence_store: Any | None = None) -> None:
        self.graph = graph
        self.evidence_store = evidence_store

    def discover(self, requirement: PieceRequirement) -> list[Piece]:
        candidates = []
        for piece in self.graph.pieces.values():
            if piece.state not in {PieceState.AVAILABLE, PieceState.VERIFIED, PieceState.CONNECTED}:
                continue
            if piece.piece_type != requirement.piece_type:
                continue
            if requirement.domain and piece.domain != requirement.domain:
                continue
            if requirement.provider_id and piece.provider_id != requirement.provider_id:
                continue
            if not requirement.capabilities.issubset(piece.capabilities):
                continue
            if requirement.truth and self._truth_rank(piece.truth) < self._truth_rank(requirement.truth):
                continue
            if any(piece.capacities.get(k) is None or piece.capacities[k].amount < v
                   for k, v in requirement.capacity.items()):
                continue
            candidates.append(piece)
        candidates.sort(key=lambda p: (self._truth_rank(p.truth), p.piece_id), reverse=True)
        return candidates

    def compose(
        self,
        intent_id: str,
        piece_requirements: list[PieceRequirement],
        connection_requirements: list[ConnectionRequirement] | None = None,
        *,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        connection_requirements = connection_requirements or []
        selected: list[Piece] = []
        used: set[str] = set()
        blockers: list[str] = []

        for requirement in piece_requirements:
            candidate = next((p for p in self.discover(requirement) if p.piece_id not in used), None)
            if candidate is None:
                blockers.append(f"NO_PIECE:{requirement.piece_type}")
                continue
            selected.append(candidate)
            used.add(candidate.piece_id)

        if blockers:
            return {"ok": False, "status": "COMPOSITION_BLOCKED", "intent_id": intent_id,
                    "piece_ids": [], "connection_ids": [], "blockers": blockers}

        connections = self._resolve_connections(selected, connection_requirements)
        if connections["blockers"]:
            return {"ok": False, "status": "CONNECTION_PLAN_BLOCKED", "intent_id": intent_id,
                    "piece_ids": [p.piece_id for p in selected],
                    "connection_ids": [], "blockers": connections["blockers"]}

        reservation = self.graph.reserve_graph(
            intent_id,
            [p.piece_id for p in selected],
            connections["connection_ids"],
            ttl_seconds=ttl_seconds,
        )
        if not reservation["ok"]:
            return {"ok": False, "status": "GRAPH_RESERVATION_BLOCKED",
                    "intent_id": intent_id, "plan": reservation}

        return {
            "ok": True,
            "status": "COMPOSED",
            "intent_id": intent_id,
            "piece_ids": [p.piece_id for p in selected],
            "connection_ids": connections["connection_ids"],
            "reservation": reservation["reservation"],
        }

    def replace_piece(
        self,
        intent_id: str,
        old_piece_id: str,
        replacement_requirement: PieceRequirement,
        *,
        connection_requirements: list[ConnectionRequirement] | None = None,
        ttl_seconds: int = 300,
        activate: bool = False,
        verification_evidence_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Replace one piece while preserving unrelated graph identity.

        The operation is guarded by a deep snapshot. If planning, verification,
        reservation, or attachment fails, the graph is restored to its prior
        state. The old piece is only quarantined after the replacement candidate
        and its required connections have been validated.
        """
        old = self.graph._require_piece(old_piece_id)
        if old.state in {PieceState.FAULTED, PieceState.OFFLINE, PieceState.QUARANTINED}:
            return {"ok": False, "status": "OLD_PIECE_UNAVAILABLE", "piece_id": old_piece_id}

        snapshot = self._snapshot_internal()
        old_connections = [
            c for c in self.graph.connections.values()
            if old_piece_id in {c.source_piece_id, c.target_piece_id}
        ]
        candidate = next(
            (p for p in self.discover(replacement_requirement) if p.piece_id != old_piece_id),
            None,
        )
        if candidate is None:
            return {"ok": False, "status": "REPLACEMENT_NOT_FOUND", "old_piece_id": old_piece_id}

        blockers = self._verify_candidate(candidate, verification_evidence_ids or [])
        if blockers:
            return {"ok": False, "status": "REPLACEMENT_VERIFICATION_BLOCKED",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "blockers": blockers}

        connection_requirements = connection_requirements or self._infer_connection_requirements(old, old_connections)
        planned = self._plan_replacement_connections(candidate, connection_requirements, old_connections)
        if planned["blockers"]:
            return {"ok": False, "status": "REPLACEMENT_CONNECTIONS_BLOCKED",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "blockers": planned["blockers"]}

        # Reserve the replacement piece + all required connections before mutating
        # the old graph. This is the key no-half-replacement boundary.
        reservation = self.graph.reserve_graph(
            intent_id,
            [candidate.piece_id],
            planned["connection_ids"],
            ttl_seconds=ttl_seconds,
        )
        if not reservation["ok"]:
            return {"ok": False, "status": "REPLACEMENT_RESERVATION_BLOCKED",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "reservation": reservation}

        try:
            # Fence and quarantine the old piece. Existing unrelated pieces are untouched.
            self.graph.reconcile_piece(
                old_piece_id,
                PieceState.QUARANTINED,
                old.truth,
                old.evidence_ids,
            )
            for connection in old_connections:
                if connection.connection_id not in planned["connection_ids"]:
                    connection.state = PieceState.DECLARED
                    connection.fencing_epoch += 1

            # Attach and verify the new subgraph.
            self.graph.attach_graph(reservation["reservation"]["reservation_id"])
            if not self._verify_activation(candidate, verification_evidence_ids or []):
                raise RuntimeError("REPLACEMENT_ACTIVATION_VERIFICATION_FAILED")

            if activate:
                self.graph.activate_graph(
                    reservation["reservation"]["reservation_id"], verified=True
                )

            plan = ReplacementPlan(
                intent_id=intent_id,
                old_piece_id=old_piece_id,
                new_piece_id=candidate.piece_id,
                preserved_piece_ids=tuple(
                    p.piece_id for p in self.graph.pieces.values()
                    if p.piece_id not in {old_piece_id, candidate.piece_id}
                ),
                detached_connection_ids=tuple(
                    c.connection_id for c in old_connections
                    if c.connection_id not in planned["connection_ids"]
                ),
                planned_connection_ids=tuple(planned["connection_ids"]),
                status="ACTIVE" if activate else "ATTACHED",
            )
            self.graph._event("PIECE_REPLACED", **plan.public())
            return {"ok": True, "status": plan.status, "plan": plan.public(),
                    "reservation": reservation["reservation"]}
        except Exception as exc:
            self._restore_internal(snapshot)
            return {"ok": False, "status": "REPLACEMENT_ROLLED_BACK",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "error": str(exc)}

    def _verify_candidate(self, piece: Piece, evidence_ids: list[str]) -> list[str]:
        blockers: list[str] = []
        if piece.truth not in {TruthLevel.VERIFIED, TruthLevel.ATTESTED}:
            blockers.append("PIECE_TRUTH_NOT_VERIFIED")
        if piece.health in {"FAILED", "OFFLINE"}:
            blockers.append("PIECE_UNHEALTHY")
        if evidence_ids:
            if self.evidence_store is None:
                blockers.append("EVIDENCE_STORE_REQUIRED")
            else:
                for evidence_id in evidence_ids:
                    try:
                        self.evidence_store.get_valid(evidence_id, component_id=piece.piece_id)
                    except Exception as exc:
                        blockers.append(f"EVIDENCE_INVALID:{evidence_id}:{exc}")
        return blockers

    def _verify_activation(self, piece: Piece, evidence_ids: list[str]) -> bool:
        if piece.truth not in {TruthLevel.VERIFIED, TruthLevel.ATTESTED}:
            return False
        if evidence_ids and self.evidence_store is not None:
            return all(
                self._valid_evidence(eid, piece.piece_id) for eid in evidence_ids
            )
        return True

    def _valid_evidence(self, evidence_id: str, piece_id: str) -> bool:
        try:
            self.evidence_store.get_valid(evidence_id, component_id=piece_id)
            return True
        except Exception:
            return False

    def _resolve_connections(
        self,
        selected: list[Piece],
        requirements: list[ConnectionRequirement],
    ) -> dict[str, Any]:
        ids: list[str] = []
        blockers: list[str] = []
        for req in requirements:
            matches = [
                c for c in self.graph.connections.values()
                if self._connection_matches(c, req, selected)
            ]
            if not matches:
                blockers.append(
                    f"NO_CONNECTION:{req.source_piece_type}:{req.target_piece_type}:{req.connection_type.value}"
                )
                continue
            matches.sort(key=lambda c: (self._truth_rank(c.truth), c.connection_id), reverse=True)
            ids.append(matches[0].connection_id)
        return {"connection_ids": ids, "blockers": blockers}

    def _plan_replacement_connections(
        self,
        candidate: Piece,
        requirements: list[ConnectionRequirement],
        old_connections: list[Connection],
    ) -> dict[str, Any]:
        ids: list[str] = []
        blockers: list[str] = []
        if not requirements:
            # A replacement without declared requirements is safe only when the
            # graph has no existing dependency edges that would need recreation.
            return {"connection_ids": [], "blockers": []}
        for req in requirements:
            matches = [
                c for c in self.graph.connections.values()
                if c.connection_id not in {x.connection_id for x in old_connections}
                and self._connection_matches(c, req, [candidate])
            ]
            if not matches:
                blockers.append(
                    f"NO_REPLACEMENT_CONNECTION:{req.connection_type.value}"
                )
                continue
            matches.sort(key=lambda c: (self._truth_rank(c.truth), c.connection_id), reverse=True)
            ids.append(matches[0].connection_id)
        return {"connection_ids": ids, "blockers": blockers}

    def _infer_connection_requirements(
        self, old: Piece, old_connections: list[Connection]
    ) -> list[ConnectionRequirement]:
        result = []
        for c in old_connections:
            other_id = c.target_piece_id if c.source_piece_id == old.piece_id else c.source_piece_id
            other = self.graph.pieces.get(other_id)
            if other:
                result.append(ConnectionRequirement(
                    source_piece_type=old.piece_type,
                    target_piece_type=other.piece_type,
                    connection_type=c.connection_type,
                    min_bandwidth=c.bandwidth,
                ))
        return result

    def _connection_matches(
        self,
        connection: Connection,
        requirement: ConnectionRequirement,
        selected: list[Piece],
    ) -> bool:
        if connection.connection_type != requirement.connection_type:
            return False
        if requirement.min_bandwidth is not None and (
            connection.bandwidth is None or connection.bandwidth < requirement.min_bandwidth
        ):
            return False
        types = {self.graph.pieces[connection.source_piece_id].piece_type,
                 self.graph.pieces[connection.target_piece_id].piece_type}
        wanted = {requirement.source_piece_type, requirement.target_piece_type}
        if not wanted.issubset(types):
            return False
        if selected and not any(
            connection.source_piece_id == p.piece_id or connection.target_piece_id == p.piece_id
            for p in selected
        ):
            return False
        return connection.state in {
            PieceState.CONNECTED, PieceState.AVAILABLE, PieceState.VERIFIED
        }

    @staticmethod
    def _truth_rank(truth: TruthLevel) -> int:
        return {
            TruthLevel.SIMULATED: 0,
            TruthLevel.OBSERVED: 1,
            TruthLevel.VERIFIED: 2,
            TruthLevel.ATTESTED: 3,
        }[truth]

    def _snapshot_internal(self) -> tuple[Any, ...]:
        return (
            deepcopy(self.graph.pieces),
            deepcopy(self.graph.connections),
            deepcopy(self.graph.reservations),
            deepcopy(self.graph._piece_leases),
            deepcopy(self.graph._connection_leases),
            deepcopy(self.graph._epochs),
            deepcopy(self.graph.events),
        )

    def _restore_internal(self, snapshot: tuple[Any, ...]) -> None:
        (
            self.graph.pieces,
            self.graph.connections,
            self.graph.reservations,
            self.graph._piece_leases,
            self.graph._connection_leases,
            self.graph._epochs,
            self.graph.events,
        ) = snapshot
