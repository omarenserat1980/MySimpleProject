from tools.phase_21_gate import phase21_restart_recovery


def test_phase21_restart_recovery():
    result = phase21_restart_recovery()
    assert result["status"] == "PASS"
    assert result["checkpoint_restored"] is True
    assert result["resume_action"] == "RESUME"
