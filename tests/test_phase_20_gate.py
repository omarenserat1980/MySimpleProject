from tools.phase_20_gate import phase20_brain_artifact_only


def test_phase20_brain_artifact_only():
    result = phase20_brain_artifact_only()
    assert result["status"] == "PASS"
    assert result["verified"] is True
    assert len(result["sha256"]) == 64
