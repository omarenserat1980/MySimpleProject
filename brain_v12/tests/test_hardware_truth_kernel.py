from pathlib import Path

from brain_v12.brain.hardware_truth_kernel import HardwareTruthKernel
from brain_v12.brain.piece_graph import (
    HardwareGraph, Piece, PieceState, TruthLevel, Connection,
    ConnectionType,
)
from brain_v12.brain.resource_fabric import ResourceFabric, ResourceSpec, ResourceKind


def test_persistence_restores_graph(tmp_path: Path):
    path = tmp_path / "truth.json"
    g = HardwareGraph()
    g.add_piece(Piece(
        "cpu0", "CPU", "compute", "host",
        state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED,
    ))
    g.add_piece(Piece(
        "board0", "MOTHERBOARD", "platform", "host",
        state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED,
    ))
    g.add_connection(Connection(
        "pcie0", "cpu0", "board0", ConnectionType.PCIe, "host",
        state=PieceState.CONNECTED, truth=TruthLevel.VERIFIED,
    ))
    kernel = HardwareTruthKernel(g, state_path=path)
    kernel.persist()

    restored = HardwareGraph()
    HardwareTruthKernel(restored, state_path=path)
    assert "cpu0" in restored.pieces
    assert "pcie0" in restored.connections
    assert restored.pieces["cpu0"].truth == TruthLevel.VERIFIED


def test_cross_fabric_failure_compensates_graph(tmp_path: Path):
    g = HardwareGraph()
    g.add_piece(Piece("cpu0", "CPU", "compute", "host",
                      state=PieceState.AVAILABLE, truth=TruthLevel.VERIFIED))
    fabric = ResourceFabric()
    fabric.register(ResourceSpec("ram0", ResourceKind.MEMORY, "host", 4, "GB"))
    kernel = HardwareTruthKernel(g, fabric, tmp_path / "truth.json")

    result = kernel.reserve_transaction(
        "i1", ["cpu0"], [],
        resource_allocations=[{"resource_id": "missing", "amount": 1}],
    )
    assert not result["ok"]
    assert result["status"] == "TRANSACTION_ROLLED_BACK"
    assert g.pieces["cpu0"].state == PieceState.AVAILABLE


def test_reconcile_rejects_stale_observation(tmp_path: Path):
    g = HardwareGraph()
    g.add_piece(Piece(
        "cpu0", "CPU", "compute", "host",
        state=PieceState.AVAILABLE, truth=TruthLevel.OBSERVED,
        metadata={"last_observed_at": 100.0},
    ))
    kernel = HardwareTruthKernel(g, state_path=tmp_path / "truth.json")
    result = kernel.reconcile(
        "cpu0",
        observed_state=PieceState.ACTIVE,
        observed_truth=TruthLevel.VERIFIED,
        evidence_ids=["ev-1"],
        observed_at=99.0,
    )
    assert result["status"] == "STALE_OBSERVATION"


def test_reconcile_requires_evidence_for_verified_truth(tmp_path: Path):
    g = HardwareGraph()
    g.add_piece(Piece(
        "cpu0", "CPU", "compute", "host",
        state=PieceState.AVAILABLE, truth=TruthLevel.OBSERVED,
    ))
    kernel = HardwareTruthKernel(g, state_path=tmp_path / "truth.json")
    result = kernel.reconcile(
        "cpu0",
        observed_state=PieceState.VERIFIED,
        observed_truth=TruthLevel.VERIFIED,
        evidence_ids=[],
    )
    assert result["status"] == "EVIDENCE_REQUIRED_FOR_TRUTH_PROMOTION"
