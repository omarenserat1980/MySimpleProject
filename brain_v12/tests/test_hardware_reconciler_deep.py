from brain_v12.brain.hardware_reconciler import HardwareReconciler, Observation, DriftKind
from brain_v12.brain.piece_graph import HardwareGraph, Piece, PieceState, TruthLevel


def test_reconciler_rejects_stale_observation():
    g = HardwareGraph()
    g.add_piece(Piece("cpu0", "CPU", "compute", "host",
                      state=PieceState.ACTIVE, truth=TruthLevel.VERIFIED))
    r = HardwareReconciler(graph=g)
    result = r.reconcile_piece(
        Observation("cpu0", "cpu-1", {}, "HEALTHY", True,
                    state=PieceState.ACTIVE, truth=TruthLevel.VERIFIED,
                    evidence_ids=("ev-1",)),
        observed_at=100.0,
    )
    assert result["ok"]
    stale = r.reconcile_piece(
        Observation("cpu0", "cpu-1", {}, "HEALTHY", True,
                    state=PieceState.ACTIVE, truth=TruthLevel.VERIFIED,
                    evidence_ids=("ev-2",)),
        observed_at=99.0,
    )
    assert stale["status"] == "STALE_OBSERVATION"


def test_identity_conflict_quarantines_piece():
    g = HardwareGraph()
    g.add_piece(Piece("gpu0", "GPU", "accelerator", "host",
                      state=PieceState.ACTIVE, truth=TruthLevel.VERIFIED,
                      identity={"serial": "A"}))
    r = HardwareReconciler(graph=g)
    result = r.reconcile_piece(
        Observation("gpu0", "gpu-1", {}, "HEALTHY", True,
                    state=PieceState.ACTIVE, truth=TruthLevel.VERIFIED,
                    evidence_ids=("ev-1",)),
        observed_at=200.0,
    )
    assert result["status"] == "RECONCILED"


def test_compare_identity_drift_quarantines():
    r = HardwareReconciler()
    result = r.compare(
        {"identity": "A", "capacity": {}, "health": "HEALTHY", "attached": True},
        Observation("gpu0", "B", {}, "HEALTHY", True),
        observed_at=100.0, now=100.0,
    )
    assert result["drift"] == DriftKind.IDENTITY.value
