from tools.phase_18_19_gate import phase18_brain_git_only, phase19_brain_scheduler_only


def test_phase18_brain_git_only_gate():
    result = phase18_brain_git_only()
    assert result["status"] == "PASS"
    assert len(result["commit"]) == 40


def test_phase19_brain_scheduler_only_gate():
    result = phase19_brain_scheduler_only()
    assert result["status"] == "PASS"
