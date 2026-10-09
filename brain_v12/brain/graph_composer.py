from __future__ import annotations

"""Piece-first graph composer and independent piece replacement."""

from dataclasses import dataclass
from copy import deepcopy
from typing import Any

from .piece_graph import (
    HardwareGraph, Piece, PieceRequirement, Connection, ConnectionRequirement,
    PieceState, TruthLevel,
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

    def public(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "old_piece_id": self.old_piece_id,
            "new_piece_id": self.new_piece_id,
            "preserved_piece_ids": list(self.preserved_piece_ids),
            "detached_connection_ids": list(self.detached_connection_ids),
            "planned_connection_ids": list(self.planned_connection_ids),
            "status": self.status,
        }


class GraphComposer:
    """Plans and replaces graph pieces without rebuilding unrelated pieces."""

    def __init__(self, graph: HardwareGraph, evidence_store: Any | None = None) -> None:
        self.graph = graph
        self.evidence_store = evidence_store

    @staticmethod
    def _truth_rank(truth: TruthLevel) -> int:
        return {
            TruthLevel.SIMULATED: 0, TruthLevel.OBSERVED: 1,
            TruthLevel.VERIFIED: 2, TruthLevel.ATTESTED: 3,
        }[truth]

    def discover(self, requirement: PieceRequirement) -> list[Piece]:
        result = []
        for p in self.graph.pieces.values():
            if p.state not in {PieceState.AVAILABLE, PieceState.VERIFIED, PieceState.CONNECTED}:
                continue
            if p.piece_type != requirement.piece_type:
                continue
            if requirement.domain and p.domain != requirement.domain:
                continue
            if requirement.provider_id and p.provider_id != requirement.provider_id:
                continue
            if not requirement.capabilities.issubset(p.capabilities):
                continue
            if requirement.truth and self._truth_rank(p.truth) < self._truth_rank(requirement.truth):
                continue
            if any(p.capacities.get(k) is None or p.capacities[k].amount < amount
                   for k, amount in requirement.capacity.items()):
                continue
            result.append(p)
        result.sort(key=lambda p: (self._truth_rank(p.truth), p.piece_id), reverse=True)
        return result

    def compose(self, intent_id: str, piece_requirements: list[PieceRequirement],
                connection_requirements: list[ConnectionRequirement] | None = None,
                *, ttl_seconds: int = 300) -> dict[str, Any]:
        selected: list[Piece] = []
        used: set[str] = set()
        blockers: list[str] = []
        for req in connection_requirements or []:
            if req.source_piece_type == req.target_piece_type:
                continue
        for req in piece_requirements:
            candidate = next((p for p in self.discover(req) if p.piece_id not in used), None)
            if candidate is None:
                blockers.append(f"NO_PIECE:{req.piece_type}")
            else:
                selected.append(candidate)
                used.add(candidate.piece_id)
        if blockers:
            return {"ok": False, "status": "COMPOSITION_BLOCKED",
                    "intent_id": intent_id, "blockers": blockers}
        connection_ids, connection_blockers = self._resolve_connections(
            selected, connection_requirements or []
        )
        if connection_blockers:
            return {"ok": False, "status": "CONNECTION_PLAN_BLOCKED",
                    "intent_id": intent_id, "blockers": connection_blockers}
        reservation = self.graph.reserve_graph(
            intent_id, [p.piece_id for p in selected], connection_ids, ttl_seconds
        )
        if not reservation["ok"]:
            return {"ok": False, "status": "GRAPH_RESERVATION_BLOCKED",
                    "intent_id": intent_id, "reservation": reservation}
        return {"ok": True, "status": "COMPOSED", "intent_id": intent_id,
                "piece_ids": [p.piece_id for p in selected],
                "connection_ids": connection_ids,
                "reservation": reservation["reservation"]}

    def replace_piece(self, intent_id: str, old_piece_id: str,
                      replacement_requirement: PieceRequirement, *,
                      connection_requirements: list[ConnectionRequirement] | None = None,
                      ttl_seconds: int = 300, activate: bool = True,
                      verification_evidence_ids: list[str] | None = None) -> dict[str, Any]:
        old = self.graph._require_piece(old_piece_id)
        if old.state in {PieceState.FAULTED, PieceState.OFFLINE, PieceState.QUARANTINED}:
            return {"ok": False, "status": "OLD_PIECE_UNAVAILABLE", "piece_id": old_piece_id}

        snapshot = self._snapshot()
        old_connections = [
            c for c in self.graph.connections.values()
            if old_piece_id in {c.source_piece_id, c.target_piece_id}
        ]
        candidate = next(
            (p for p in self.discover(replacement_requirement) if p.piece_id != old_piece_id),
            None,
        )
        if candidate is None:
            return {"ok": False, "status": "REPLACEMENT_NOT_FOUND",
                    "old_piece_id": old_piece_id}

        blockers = self._verify_candidate(candidate, verification_evidence_ids or [])
        if blockers:
            return {"ok": False, "status": "REPLACEMENT_VERIFICATION_BLOCKED",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "blockers": blockers}

        requirements = connection_requirements or self._infer_requirements(old, old_connections)
        new_connection_ids, blockers = self._materialize_connections(
            old_piece_id, candidate, requirements, old_connections
        )
        if blockers:
            self._restore(snapshot)
            return {"ok": False, "status": "REPLACEMENT_CONNECTIONS_BLOCKED",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "blockers": blockers}

        reservation = self.graph.reserve_graph(
            intent_id, [candidate.piece_id], new_connection_ids, ttl_seconds
        )
        if not reservation["ok"]:
            self._restore(snapshot)
            return {"ok": False, "status": "REPLACEMENT_RESERVATION_BLOCKED",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "reservation": reservation}
        try:
            self.graph.reconcile_piece(
                old_piece_id, PieceState.QUARANTINED, old.truth, old.evidence_ids
            )
            for c in old_connections:
                c.state = PieceState.DECLARED
                c.fencing_epoch += 1
            self.graph.attach_graph(reservation["reservation"]["reservation_id"])
            if not self._verify_candidate(candidate, verification_evidence_ids or []):
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
                detached_connection_ids=tuple(c.connection_id for c in old_connections),
                planned_connection_ids=tuple(new_connection_ids),
                status="ACTIVE" if activate else "ATTACHED",
            )
            self.graph._event("PIECE_REPLACED", **plan.public())
            return {"ok": True, "status": plan.status, "plan": plan.public(),
                    "reservation": reservation["reservation"]}
        except Exception as exc:
            self._restore(snapshot)
            return {"ok": False, "status": "REPLACEMENT_ROLLED_BACK",
                    "old_piece_id": old_piece_id, "new_piece_id": candidate.piece_id,
                    "error": str(exc)}

    def _verify_candidate(self, piece: Piece, evidence_ids: list[str]) -> list[str]:
        blockers = []
        if piece.truth not in {TruthLevel.VERIFIED, TruthLevel.ATTESTED}:
            blockers.append("PIECE_TRUTH_NOT_VERIFIED")
        if piece.health in {"FAILED", "OFFLINE"}:
            blockers.append("PIECE_UNHEALTHY")
        for eid in evidence_ids:
            if self.evidence_store is None:
                blockers.append("EVIDENCE_STORE_REQUIRED")
                break
            try:
                self.evidence_store.get_valid(eid, component_id=piece.piece_id)
            except Exception as exc:
                blockers.append(f"EVIDENCE_INVALID:{eid}:{exc}")
        return blockers

    def _infer_requirements(self, old: Piece, old_connections: list[Connection]):
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

    def _materialize_connections(self, old_id: str, candidate: Piece,
                                 requirements: list[ConnectionRequirement],
                                 old_connections: list[Connection]):
        ids = []
        blockers = []
        for req in requirements:
            template = next(
                (c for c in old_connections
                 if c.connection_type == req.connection_type
                 and (req.min_bandwidth is None or (
                     c.bandwidth is not None and c.bandwidth >= req.min_bandwidth))),
                None,
            )
            if template is None:
                blockers.append(f"NO_REPLACEMENT_EDGE_TEMPLATE:{req.connection_type.value}")
                continue
            other_id = (
                template.target_piece_id
                if template.source_piece_id == old_id
                else template.source_piece_id
            )
            other = self.graph.pieces.get(other_id)
            if other is None:
                blockers.append(f"REPLACEMENT_ENDPOINT_MISSING:{other_id}")
                continue
            if {candidate.piece_type, other.piece_type} != {
                req.source_piece_type, req.target_piece_type
            }:
                blockers.append(f"REPLACEMENT_ENDPOINT_TYPE_MISMATCH:{req.connection_type.value}")
                continue
            cid = f"conn-{candidate.piece_id}-{template.connection_type.value}-{other_id}"
            if cid not in self.graph.connections:
                self.graph.add_connection(Connection(
                    connection_id=cid,
                    source_piece_id=candidate.piece_id,
                    target_piece_id=other_id,
                    connection_type=template.connection_type,
                    provider_id=candidate.provider_id,
                    backend=candidate.backend or template.backend,
                    state=PieceState.AVAILABLE,
                    truth=min((candidate.truth, template.truth), key=self._truth_rank),
                    direction=template.direction,
                    latency=template.latency,
                    bandwidth=template.bandwidth,
                    protocol=template.protocol,
                    metadata={**template.metadata, "replacement_of": template.connection_id},
                    evidence_ids=list(candidate.evidence_ids),
                ))
            ids.append(cid)
        return ids, blockers

    def _resolve_connections(self, selected, requirements):
        ids, blockers = [], []
        for req in requirements:
            match = next((
                c for c in self.graph.connections.values()
                if c.connection_type == req.connection_type
                and {self.graph.pieces[c.source_piece_id].piece_type,
                     self.graph.pieces[c.target_piece_id].piece_type}
                   == {req.source_piece_type, req.target_piece_type}
                and (req.min_bandwidth is None or (
                    c.bandwidth is not None and c.bandwidth >= req.min_bandwidth))
                and any(c.source_piece_id == p.piece_id or c.target_piece_id == p.piece_id
                        for p in selected)
                and c.state in {PieceState.CONNECTED, PieceState.AVAILABLE, PieceState.VERIFIED}
            ), None)
            if match:
                ids.append(match.connection_id)
            else:
                blockers.append(f"NO_CONNECTION:{req.connection_type.value}")
        return ids, blockers

    def _snapshot(self):
        return (
            deepcopy(self.graph.pieces), deepcopy(self.graph.connections),
            deepcopy(self.graph.reservations), deepcopy(self.graph._piece_leases),
            deepcopy(self.graph._connection_leases), deepcopy(self.graph._epochs),
            deepcopy(self.graph.events),
        )

    def _restore(self, snapshot):
        (self.graph.pieces, self.graph.connections, self.graph.reservations,
         self.graph._piece_leases, self.graph._connection_leases,
         self.graph._epochs, self.graph.events) = snapshot
