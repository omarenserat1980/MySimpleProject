from cloud.release_gate import Gate, ReleaseGate

def test_release_gate_blocks_when_required_gate_fails(tmp_path, monkeypatch):
    gate = ReleaseGate(tmp_path)

    monkeypatch.setattr(gate, "_compile", lambda: Gate("compile", True, True, "test://compile"))
    monkeypatch.setattr(gate, "_pytest_feedback", lambda: Gate("feedback_contract", True, True, "test://feedback"))
    monkeypatch.setattr(gate, "_pytest_task_engine", lambda: Gate("task_engine_evidence_contract", True, False, "test://task"))
    monkeypatch.setattr(gate, "_api_routes", lambda: Gate("api_routes", True, True, "test://api"))
    monkeypatch.setattr(gate, "_cinema_truth", lambda: Gate("cinema_truth", True, True, "test://cinema"))
    monkeypatch.setattr(gate, "_governance", lambda: Gate("governance", True, True, "test://governance"))

    result = gate.run()
    assert result["status"] == "RELEASE_BLOCKED"
    assert result["evidence_contract"]["all_required_gates_passed"] is False
    assert (tmp_path / "release_gate" / "release_gate.json").exists()

def test_release_gate_records_evidence_contract(tmp_path, monkeypatch):
    gate = ReleaseGate(tmp_path)
    passed = lambda name: Gate(name, True, True, f"test://{name}")
    monkeypatch.setattr(gate, "_compile", lambda: passed("compile"))
    monkeypatch.setattr(gate, "_pytest_feedback", lambda: passed("feedback_contract"))
    monkeypatch.setattr(gate, "_pytest_task_engine", lambda: passed("task_engine_evidence_contract"))
    monkeypatch.setattr(gate, "_api_routes", lambda: passed("api_routes"))
    monkeypatch.setattr(gate, "_cinema_truth", lambda: passed("cinema_truth"))
    monkeypatch.setattr(gate, "_governance", lambda: passed("governance"))

    result = gate.run()
    assert result["status"] == "RELEASE_ALLOWED"
    assert result["evidence_contract"]["all_required_gates_passed"] is True
    assert result["evidence_contract"]["release_requires_runtime_evidence"] is True
