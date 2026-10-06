from brain_v12.self_healing.deep_execution_evidence_gate import DeepEvidenceGate

def test_planned_is_not_verified(tmp_path):
    state_dir = tmp_path / "deep"
    state_dir.mkdir()
    (state_dir / "deep_execution_checkpoint.json").write_text("{}", encoding="utf-8")
    gate = DeepEvidenceGate(state_dir)
    state = {
        "depth": 2,
        "last_run": {"executed": 1, "failed": 0},
        "history": [{"result": {"status": "PLANNED"}}],
    }
    assert gate.evaluate(state)["status"] == "FAILED"

def test_verified_batch(tmp_path):
    state_dir = tmp_path / "deep"
    state_dir.mkdir()
    (state_dir / "deep_execution_checkpoint.json").write_text("{}", encoding="utf-8")
    gate = DeepEvidenceGate(state_dir)
    state = {
        "depth": 2,
        "last_run": {"executed": 1, "failed": 0},
        "history": [{"result": {"status": "VERIFIED"}}],
    }
    assert gate.evaluate(state)["status"] == "VERIFIED"
