from pathlib import Path

import cloud.release_gate as release_gate


def test_release_gate_blocks_when_live_autonomy_is_not_proven(monkeypatch, tmp_path):
    gate = release_gate.ReleaseGate(tmp_path)
    monkeypatch.setattr(
        gate,
        "_compile",
        lambda: release_gate.Gate("compile", True, True, "test://compile"),
    )
    monkeypatch.setattr(
        gate,
        "_pytest_feedback",
        lambda: release_gate.Gate("feedback_contract", True, True, "test://feedback"),
    )
    monkeypatch.setattr(
        gate,
        "_pytest_task_engine",
        lambda: release_gate.Gate("task_engine_evidence_contract", True, True, "test://task"),
    )
    monkeypatch.setattr(
        gate,
        "_api_routes",
        lambda: release_gate.Gate("api_routes", True, True, "test://api"),
    )
    monkeypatch.setattr(
        gate,
        "_quran_layer",
        lambda: release_gate.Gate("quran_layer_evidence", True, True, "test://quran"),
    )
    monkeypatch.setattr(
        gate,
        "_cinema_truth",
        lambda: release_gate.Gate("cinema_truth", True, True, "test://cinema"),
    )
    monkeypatch.setattr(
        gate,
        "_governance",
        lambda: release_gate.Gate("governance", True, True, "test://governance"),
    )
    monkeypatch.setattr(
        gate,
        "_independence_contract",
        lambda: release_gate.Gate("independence_contract", True, True, "test://contract"),
    )
    monkeypatch.setattr(
        release_gate,
        "evaluate_autonomy",
        lambda: {
            "AUTONOMOUS_WITHIN_AUTHORITY": False,
            "scoped_independence_proven": True,
            "live_brain_executor_ready": False,
        },
    )

    result = gate.run()
    assert result["status"] == "RELEASE_BLOCKED"
    autonomy = next(g for g in result["gates"] if g["name"] == "autonomous_within_authority")
    assert autonomy["passed"] is False
