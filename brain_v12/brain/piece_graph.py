from __future__ import annotations

"""Piece-first composable hardware graph.

A cloud/server is a projection of independent pieces and first-class connections.
This module is deliberately backend-neutral and does not claim physical truth.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import uuid


class PieceState(str, Enum):
    DECLARED = "DECLARED"
    DISCOVERED = "DISCOVERED"
    PROVISIONED = "PROVISIONED"
    VERIFIED = "VERIFIED"
    CONNECTED = "CONNECTED"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    ATTACHED = "ATTACHED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    OFFLINE = "OFFLINE"
    FAULTED = "FAULTED"
    QUARANTINED = "QUARANTINED"
    RECOVERING = "RECOVERING"


class TruthLevel(str, Enum):
    SIMULATED = "SIMULATED"
    OBSERVED = "OBSERVED"
    VERIFIED = "VERIFIED"
    ATTESTED = "ATTESTED"


class CapacityOrigin(str, Enum):
    PHYSICAL = "PHYSICAL"
    DERIVED = "DERIVED"
    VIRTUAL = "VIRTUAL"


class ConnectionType(str, Enum):
    POWER = "POWER"
    THERMAL = "THERMAL"
    PCIe = "PCIe"
    MEMORY = "MEMORY"
    NUMA = "NUMA"
    DMA = "DMA"
    IRQ = "IRQ"
    NETWORK = "NETWORK"
    STORAGE = "STORAGE"
    CONTROL = "CONTROL"
    MANAGEMENT = "MANAGEMENT"
    SECURITY = "SECURITY"
    CLOCK = "CLOCK"
    FIRMWARE = "FIRMWARE"


@dataclass(frozen=True)
class Capacity:
    name: str
    amount: float
    unit: str
    origin: CapacityOrigin
    owner_piece_id: str
    allocatable: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("PIECE_CAPACITY_NEGATIVE")
        if not self.owner_piece_id:
            raise ValueError("PIECE_CAPACITY_OWNER_REQUIRED")


@dataclass
class Piece:
    piece_id: str
    piece_type: str
    domain: str
    provider_id: str
    backend: str | None = None
    parent_id: str | None = None
    state: PieceState = PieceState.DECLARED
    truth: TruthLevel = TruthLevel.SIMULATED
    capabilities: set[str] = field(default_factory=set)
    capacities: dict[str, Capacity] = field(default_factory=dict)
    identity: dict[str, Any] = field(default_factory=dict)
    health: str = "UNKNOWN"
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    fencing_epoch: int = 0

    def add_capacity(self, capacity: Capacity) -> None:
        if capacity.owner_piece_id != self.piece_id:
            raise ValueError("PIECE_CAPACITY_OWNER_MISMATCH")
        if capacity.name in self.capacities:
            raise ValueError("PIECE_CAPACITY_EXISTS")
        self.capacities[capacity.name] = capacity


@dataclass
class Connection:
    connection_id: str
    source_piece_id: str
    target_piece_id: str
    connection_type: ConnectionType
    provider_id: str
    backend: str | None = None
    state: PieceState = PieceState.DECLARED
    truth: TruthLevel = TruthLevel.SIMULATED
    capacity: Capacity | None = None
    direction: str = "BIDIRECTIONAL"
    latency: float | None = None
    bandwidth: float | None = None
    protocol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    fencing_epoch: int = 0


@dataclass(frozen=True)
class PieceRequirement:
    piece_type: str
    domain: str | None = None
    provider_id: str | None = None
    capabilities: frozenset[str] = frozenset()
    capacity: dict[str, float] = field(default_factory=dict)
    truth: TruthLevel | None = None


@dataclass(frozen=True)
class ConnectionRequirement:
    source_piece_type: str
    target_piece_type: str
    connection_type: ConnectionType
    min_bandwidth: float | None = None


@dataclass
class GraphReservation:
    reservation_id: str
    intent_id: str
    piece_ids: tuple[str, ...]
    connection_ids: tuple[str, ...]
    fencing_epoch: int
    created_at: float
    expires_at: float
    status: str = "RESERVED"


class HardwareGraph:
    """Authoritative in-memory graph for composable pieces and connections."""

    def __init__(self) -> None:
        self.pieces: dict[str, Piece] = {}
        self.connections: dict[str, Connection] = {}
        self.reservations: dict[str, GraphReservation] = {}
        self._piece_leases: dict[str, str] = {}
        self._connection_leases: dict[str, str] = {}
        self._epochs: dict[str, int] = {}
        self.events: list[dict[str, Any]] = []

    def add_piece(self, piece: Piece) -> None:
        if piece.piece_id in self.pieces:
            raise ValueError("PIECE_EXISTS")
        self.pieces[piece.piece_id] = piece
        self._epochs.setdefault(piece.piece_id, piece.fencing_epoch)
        self._event("PIECE_ADDED", piece_id=piece.piece_id)

    def add_connection(self, connection: Connection) -> None:
        if connection.connection_id in self.connections:
            raise ValueError("CONNECTION_EXISTS")
        self._require_piece(connection.source_piece_id)
        self._require_piece(connection.target_piece_id)
        if connection.source_piece_id == connection.target_piece_id:
            raise ValueError("SELF_CONNECTION_FORBIDDEN")
        self.connections[connection.connection_id] = connection
        self._epochs.setdefault(connection.connection_id, connection.fencing_epoch)
        self._event("CONNECTION_ADDED", connection_id=connection.connection_id)

    def connected(self, source: str, target: str,
                  connection_type: ConnectionType | None = None) -> bool:
        return any(
            c.state in {PieceState.CONNECTED, PieceState.AVAILABLE, PieceState.RESERVED,
                        PieceState.ATTACHED, PieceState.ACTIVE}
            and {c.source_piece_id, c.target_piece_id} == {source, target}
            and (connection_type is None or c.connection_type == connection_type)
            for c in self.connections.values()
        )

    def connect(self, connection_id: str, *, evidence_ids: list[str] | None = None) -> dict[str, Any]:
        c = self._require_connection(connection_id)
        source = self.pieces[c.source_piece_id]
        target = self.pieces[c.target_piece_id]
        if source.state in {PieceState.OFFLINE, PieceState.FAULTED, PieceState.QUARANTINED}:
            raise RuntimeError("CONNECTION_SOURCE_UNAVAILABLE")
        if target.state in {PieceState.OFFLINE, PieceState.FAULTED, PieceState.QUARANTINED}:
            raise RuntimeError("CONNECTION_TARGET_UNAVAILABLE")
        c.state = PieceState.CONNECTED
        if evidence_ids:
            c.evidence_ids = list(evidence_ids)
        self._event("CONNECTION_CONNECTED", connection_id=connection_id)
        return self.connection_public(connection_id)

    def reserve_graph(self, intent_id: str, piece_ids: list[str],
                      connection_ids: list[str], ttl_seconds: int = 300) -> dict[str, Any]:
        self._reap()
        pieces = sorted(set(piece_ids))
        connections = sorted(set(connection_ids))
        for pid in pieces:
            p = self._require_piece(pid)
            if p.state not in {PieceState.AVAILABLE, PieceState.VERIFIED, PieceState.CONNECTED}:
                return {"ok": False, "status": "PIECE_NOT_AVAILABLE", "piece_id": pid}
            if pid in self._piece_leases:
                return {"ok": False, "status": "PIECE_BUSY", "piece_id": pid}
        for cid in connections:
            c = self._require_connection(cid)
            if c.state not in {PieceState.CONNECTED, PieceState.AVAILABLE}:
                return {"ok": False, "status": "CONNECTION_NOT_AVAILABLE", "connection_id": cid}
            if cid in self._connection_leases:
                return {"ok": False, "status": "CONNECTION_BUSY", "connection_id": cid}
        now = time.time()
        reservation_id = f"gres-{uuid.uuid4().hex[:12]}"
        epoch = max([self._epochs.get(x, 0) for x in pieces + connections] or [0]) + 1
        reservation = GraphReservation(
            reservation_id, intent_id, tuple(pieces), tuple(connections), epoch,
            now, now + max(1, int(ttl_seconds))
        )
        self.reservations[reservation_id] = reservation
        for pid in pieces:
            self._piece_leases[pid] = reservation_id
            self._epochs[pid] = epoch
            self.pieces[pid].state = PieceState.RESERVED
            self.pieces[pid].fencing_epoch = epoch
        for cid in connections:
            self._connection_leases[cid] = reservation_id
            self._epochs[cid] = epoch
            self.connections[cid].state = PieceState.RESERVED
            self.connections[cid].fencing_epoch = epoch
        self._event("GRAPH_RESERVED", reservation_id=reservation_id, intent_id=intent_id)
        return {"ok": True, "status": "RESERVED", "reservation": self.reservation_public(reservation_id)}

    def attach_graph(self, reservation_id: str) -> dict[str, Any]:
        r = self._require_reservation(reservation_id)
        if r.status != "RESERVED":
            raise RuntimeError("GRAPH_RESERVATION_NOT_ACTIVE")
        for pid in r.piece_ids:
            self.pieces[pid].state = PieceState.ATTACHED
        for cid in r.connection_ids:
            self.connections[cid].state = PieceState.ATTACHED
        self._event("GRAPH_ATTACHED", reservation_id=reservation_id)
        return self.reservation_public(reservation_id)

    def activate_graph(self, reservation_id: str, *, verified: bool = False) -> dict[str, Any]:
        r = self._require_reservation(reservation_id)
        if r.status != "RESERVED" or not verified:
            raise RuntimeError("GRAPH_ACTIVATION_REQUIRES_VERIFICATION")
        for pid in r.piece_ids:
            self.pieces[pid].state = PieceState.ACTIVE
        for cid in r.connection_ids:
            self.connections[cid].state = PieceState.ACTIVE
        self.reservations[reservation_id] = GraphReservation(
            r.reservation_id, r.intent_id, r.piece_ids, r.connection_ids,
            r.fencing_epoch, r.created_at, r.expires_at, "ACTIVE"
        )
        self._event("GRAPH_ACTIVE", reservation_id=reservation_id)
        return self.reservation_public(reservation_id)

    def release_graph(self, reservation_id: str) -> dict[str, Any]:
        r = self._require_reservation(reservation_id)
        for pid in r.piece_ids:
            self._piece_leases.pop(pid, None)
            if pid in self.pieces and self.pieces[pid].state != PieceState.FAULTED:
                self.pieces[pid].state = PieceState.AVAILABLE
        for cid in r.connection_ids:
            self._connection_leases.pop(cid, None)
            if cid in self.connections and self.connections[cid].state != PieceState.FAULTED:
                self.connections[cid].state = PieceState.CONNECTED
        self.reservations[reservation_id] = GraphReservation(
            r.reservation_id, r.intent_id, r.piece_ids, r.connection_ids,
            r.fencing_epoch, r.created_at, r.expires_at, "RELEASED"
        )
        self._event("GRAPH_RELEASED", reservation_id=reservation_id)
        return self.reservation_public(reservation_id)

    def affected_subgraph(self, failed_piece_id: str) -> dict[str, Any]:
        self._require_piece(failed_piece_id)
        affected_pieces = {failed_piece_id}
        affected_connections = set()
        changed = True
        while changed:
            changed = False
            for cid, c in self.connections.items():
                if c.source_piece_id in affected_pieces or c.target_piece_id in affected_pieces:
                    if cid not in affected_connections:
                        affected_connections.add(cid)
                        changed = True
                    other = c.target_piece_id if c.source_piece_id in affected_pieces else c.source_piece_id
                    if c.connection_type in {ConnectionType.POWER, ConnectionType.MEMORY,
                                             ConnectionType.THERMAL, ConnectionType.CONTROL,
                                             ConnectionType.SECURITY} and other not in affected_pieces:
                        affected_pieces.add(other)
                        changed = True
        return {"piece_ids": sorted(affected_pieces), "connection_ids": sorted(affected_connections)}

    def reconcile_piece(self, piece_id: str, state: PieceState, truth: TruthLevel,
                        evidence_ids: list[str] | None = None) -> dict[str, Any]:
        p = self._require_piece(piece_id)
        p.state = state
        p.truth = truth
        if evidence_ids:
            p.evidence_ids = list(evidence_ids)
        if state in {PieceState.OFFLINE, PieceState.FAULTED, PieceState.QUARANTINED}:
            lease = self._piece_leases.pop(piece_id, None)
            if lease:
                self._event("PIECE_LEASE_FENCED", piece_id=piece_id, reservation_id=lease)
        self._event("PIECE_RECONCILED", piece_id=piece_id, state=state.value)
        return self.piece_public(piece_id)

    def snapshot(self) -> dict[str, Any]:
        return {
            "pieces": {k: self.piece_public(k) for k in sorted(self.pieces)},
            "connections": {k: self.connection_public(k) for k in sorted(self.connections)},
            "reservations": {k: self.reservation_public(k) for k in sorted(self.reservations)},
        }

    def piece_public(self, piece_id: str) -> dict[str, Any]:
        p = self._require_piece(piece_id)
        return {
            "piece_id": p.piece_id, "piece_type": p.piece_type, "domain": p.domain,
            "provider_id": p.provider_id, "backend": p.backend, "parent_id": p.parent_id,
            "state": p.state.value, "truth": p.truth.value, "capabilities": sorted(p.capabilities),
            "capacities": {k: vars(v) for k, v in p.capacities.items()},
            "identity": dict(p.identity), "health": p.health,
            "evidence_ids": list(p.evidence_ids), "fencing_epoch": p.fencing_epoch,
        }

    def connection_public(self, connection_id: str) -> dict[str, Any]:
        c = self._require_connection(connection_id)
        return {
            "connection_id": c.connection_id, "source_piece_id": c.source_piece_id,
            "target_piece_id": c.target_piece_id, "connection_type": c.connection_type.value,
            "provider_id": c.provider_id, "backend": c.backend, "state": c.state.value,
            "truth": c.truth.value, "direction": c.direction, "latency": c.latency,
            "bandwidth": c.bandwidth, "protocol": c.protocol,
            "evidence_ids": list(c.evidence_ids), "fencing_epoch": c.fencing_epoch,
        }

    def reservation_public(self, reservation_id: str) -> dict[str, Any]:
        r = self._require_reservation(reservation_id)
        return {"reservation_id": r.reservation_id, "intent_id": r.intent_id,
                "piece_ids": list(r.piece_ids), "connection_ids": list(r.connection_ids),
                "fencing_epoch": r.fencing_epoch, "created_at": r.created_at,
                "expires_at": r.expires_at, "status": r.status}

    def inspect(self) -> dict[str, Any]:
        self._reap()
        return {"piece_count": len(self.pieces), "connection_count": len(self.connections),
                "reservation_count": sum(r.status in {"RESERVED", "ACTIVE"} for r in self.reservations.values()),
                "pieces": [self.piece_public(k) for k in sorted(self.pieces)],
                "connections": [self.connection_public(k) for k in sorted(self.connections)]}

    def _reap(self) -> None:
        now = time.time()
        for rid, r in list(self.reservations.items()):
            if r.status == "RESERVED" and r.expires_at <= now:
                self.release_graph(rid)

    def _require_piece(self, piece_id: str) -> Piece:
        if piece_id not in self.pieces:
            raise KeyError("PIECE_NOT_FOUND")
        return self.pieces[piece_id]

    def _require_connection(self, connection_id: str) -> Connection:
        if connection_id not in self.connections:
            raise KeyError("CONNECTION_NOT_FOUND")
        return self.connections[connection_id]

    def _require_reservation(self, reservation_id: str) -> GraphReservation:
        if reservation_id not in self.reservations:
            raise KeyError("GRAPH_RESERVATION_NOT_FOUND")
        return self.reservations[reservation_id]

    def _event(self, event: str, **data: Any) -> None:
        self.events.append({"ts": time.time(), "event": event, **data})
