from __future__ import annotations

"""Piece-first hardware graph API.

All mutating endpoints require the Brain control key. The API exposes pieces
and connections as first-class resources and provides an atomic control-plane
replacement operation.
"""

from fastapi import APIRouter, Request
from .control_auth import require_control_key
from .graph_composer import GraphComposer
from .piece_graph import (
    Connection, ConnectionRequirement, ConnectionType, HardwareGraph,
    Piece, PieceRequirement, PieceState, TruthLevel, Capacity, CapacityOrigin,
)


def _truth(value: str | None) -> TruthLevel | None:
    return TruthLevel(value) if value else None


def _piece_requirement(data: dict) -> PieceRequirement:
    capacity = {
        str(k): float(v) for k, v in dict(data.get("capacity") or {}).items()
    }
    return PieceRequirement(
        piece_type=str(data["piece_type"]),
        domain=str(data["domain"]) if data.get("domain") else None,
        provider_id=str(data["provider_id"]) if data.get("provider_id") else None,
        capabilities=frozenset(str(x) for x in data.get("capabilities", [])),
        capacity=capacity,
        truth=_truth(data.get("truth")),
    )


def _connection_requirement(data: dict) -> ConnectionRequirement:
    return ConnectionRequirement(
        source_piece_type=str(data["source_piece_type"]),
        target_piece_type=str(data["target_piece_type"]),
        connection_type=ConnectionType(str(data["connection_type"])),
        min_bandwidth=float(data["min_bandwidth"]) if data.get("min_bandwidth") is not None else None,
    )


def build_piece_graph_router(graph: HardwareGraph, composer: GraphComposer) -> APIRouter:
    router = APIRouter()

    @router.get("/api/brain/hardware-graph")
    def graph_status():
        return graph.inspect()

    @router.get("/api/brain/hardware-graph/piece/{piece_id}")
    def graph_piece(piece_id: str):
        return graph.piece_public(piece_id)

    @router.post("/api/brain/hardware-graph/piece")
    def graph_add_piece(request: Request, body: dict):
        require_control_key(request)
        piece = Piece(
            piece_id=str(body["piece_id"]),
            piece_type=str(body["piece_type"]),
            domain=str(body["domain"]),
            provider_id=str(body["provider_id"]),
            backend=str(body["backend"]) if body.get("backend") else None,
            parent_id=str(body["parent_id"]) if body.get("parent_id") else None,
            state=PieceState(str(body.get("state", "DECLARED"))),
            truth=TruthLevel(str(body.get("truth", "SIMULATED"))),
            capabilities=set(str(x) for x in body.get("capabilities", [])),
            health=str(body.get("health", "UNKNOWN")),
            identity=dict(body.get("identity") or {}),
            metadata=dict(body.get("metadata") or {}),
            evidence_ids=[str(x) for x in body.get("evidence_ids", [])],
        )
        for name, value in dict(body.get("capacities") or {}).items():
            if isinstance(value, dict):
                piece.add_capacity(Capacity(
                    str(name), float(value["amount"]), str(value["unit"]),
                    CapacityOrigin(str(value.get("origin", "VIRTUAL"))),
                    piece.piece_id, bool(value.get("allocatable", True)),
                    dict(value.get("metadata") or {}),
                ))
        graph.add_piece(piece)
        return graph.piece_public(piece.piece_id)

    @router.post("/api/brain/hardware-graph/connect")
    def graph_connect(request: Request, body: dict):
        require_control_key(request)
        connection = Connection(
            connection_id=str(body["connection_id"]),
            source_piece_id=str(body["source_piece_id"]),
            target_piece_id=str(body["target_piece_id"]),
            connection_type=ConnectionType(str(body["connection_type"])),
            provider_id=str(body["provider_id"]),
            backend=str(body["backend"]) if body.get("backend") else None,
            state=PieceState(str(body.get("state", "DECLARED"))),
            truth=TruthLevel(str(body.get("truth", "SIMULATED"))),
            direction=str(body.get("direction", "BIDIRECTIONAL")),
            latency=float(body["latency"]) if body.get("latency") is not None else None,
            bandwidth=float(body["bandwidth"]) if body.get("bandwidth") is not None else None,
            protocol=str(body["protocol"]) if body.get("protocol") else None,
            metadata=dict(body.get("metadata") or {}),
            evidence_ids=[str(x) for x in body.get("evidence_ids", [])],
        )
        graph.add_connection(connection)
        return graph.connection_public(connection.connection_id)

    @router.post("/api/brain/hardware-graph/compose")
    def graph_compose(request: Request, body: dict):
        require_control_key(request)
        return composer.compose(
            str(body["intent_id"]),
            [_piece_requirement(x) for x in body.get("piece_requirements", [])],
            [_connection_requirement(x) for x in body.get("connection_requirements", [])],
            ttl_seconds=int(body.get("ttl_seconds", 300)),
        )

    @router.post("/api/brain/hardware-graph/replace")
    def graph_replace(request: Request, body: dict):
        require_control_key(request)
        return composer.replace_piece(
            str(body["intent_id"]),
            str(body["old_piece_id"]),
            _piece_requirement(dict(body["replacement_requirement"])),
            connection_requirements=[
                _connection_requirement(x)
                for x in body.get("connection_requirements", [])
            ] or None,
            ttl_seconds=int(body.get("ttl_seconds", 300)),
            activate=bool(body.get("activate", True)),
            verification_evidence_ids=[
                str(x) for x in body.get("verification_evidence_ids", [])
            ],
        )

    @router.post("/api/brain/hardware-graph/failure")
    def graph_failure(request: Request, body: dict):
        require_control_key(request)
        piece_id = str(body["piece_id"])
        return graph.reconcile_piece(
            piece_id, PieceState(str(body.get("state", "FAULTED"))),
            TruthLevel(str(body.get("truth", "OBSERVED"))),
            [str(x) for x in body.get("evidence_ids", [])],
        )

    return router
