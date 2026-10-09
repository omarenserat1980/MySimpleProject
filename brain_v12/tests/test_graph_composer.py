from brain_v12.brain.graph_composer import GraphComposer
from brain_v12.brain.piece_graph import (
    HardwareGraph, Piece, Connection, ConnectionType, PieceState, TruthLevel,
    PieceRequirement, Capacity, CapacityOrigin,
)


def _graph():
    g = HardwareGraph()
    board = Piece("board", "MOTHERBOARD", "platform", "host",
                  state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED)
    old = Piece("gpu-old", "GPU", "accelerator", "host",
                state=PieceState.ACTIVE, truth=TruthLevel.VERIFIED)
    new = Piece("gpu-new", "GPU", "accelerator", "host",
                state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED)
    new.add_capacity(Capacity("vram", 24, "GB", CapacityOrigin.VIRTUAL, "gpu-new"))
    for p in (board, old, new):
        g.add_piece(p)
    g.add_connection(Connection(
        "old-pcie", "gpu-old", "board", ConnectionType.PCIe, "host",
        state=PieceState.CONNECTED, truth=TruthLevel.VERIFIED, bandwidth=32.0,
    ))
    return g


def test_replace_one_piece_preserves_unrelated_piece_identity():
    g = _graph()
    composer = GraphComposer(g)
    before = g.pieces["board"]
    result = composer.replace_piece(
        "replace-gpu-1", "gpu-old",
        PieceRequirement("GPU", domain="accelerator", truth=TruthLevel.VERIFIED),
    )
    assert result["ok"]
    assert g.pieces["gpu-old"].state == PieceState.QUARANTINED
    assert g.pieces["gpu-new"].state == PieceState.ACTIVE
    assert g.pieces["board"] is before
    assert g.pieces["board"].state == PieceState.AVAILABLE
    assert g.pieces["gpu-new"].piece_id in result["plan"]["new_piece_id"]
    assert result["plan"]["detached_connection_ids"] == ["old-pcie"]
    assert any(
        c.source_piece_id == "gpu-new"
        and c.target_piece_id == "board"
        and c.connection_type == ConnectionType.PCIe
        and c.state == PieceState.ACTIVE
        for c in g.connections.values()
    )


def test_replacement_without_required_edge_rolls_back():
    g = HardwareGraph()
    old = Piece("old", "GPU", "accelerator", "host",
                state=PieceState.ACTIVE, truth=TruthLevel.VERIFIED)
    new = Piece("new", "GPU", "accelerator", "host",
                state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED)
    board = Piece("board", "MOTHERBOARD", "platform", "host",
                  state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED)
    for p in (old, new, board):
        g.add_piece(p)
    # No old connection template exists, so replacement must be blocked.
    result = GraphComposer(g).replace_piece(
        "replace-fail", "old",
        PieceRequirement("GPU", truth=TruthLevel.VERIFIED),
    )
    assert not result["ok"]
    assert result["status"] == "REPLACEMENT_CONNECTIONS_BLOCKED" or result["status"] == "REPLACEMENT_NOT_FOUND"
    assert g.pieces["old"].state == PieceState.ACTIVE
    assert g.pieces["new"].state == PieceState.AVAILABLE


def test_compose_reserves_independent_piece_and_existing_connection():
    g = _graph()
    # Add a second already-connected endpoint to prove the generic composer path.
    g.add_piece(Piece("nic", "NIC", "network", "host",
                      state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED))
    g.add_connection(Connection(
        "nic-link", "nic", "board", ConnectionType.NETWORK, "host",
        state=PieceState.CONNECTED, truth=TruthLevel.VERIFIED, bandwidth=10.0,
    ))
    result = GraphComposer(g).compose(
        "compose-1",
        [PieceRequirement("NIC", truth=TruthLevel.VERIFIED)],
    )
    assert result["ok"]
    assert result["reservation"]["piece_ids"] == ["nic"]
