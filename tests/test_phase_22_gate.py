from tools.phase_22_gate import phase22_github_optional


def test_phase22_github_optional():
    result = phase22_github_optional()
    assert result["status"] == "PASS"
    assert result["github_dependency"] == "OPTIONAL"
    assert result["brain_executor_selected"] == "brain-local-01"
    assert result["external_only_decision"] == "BLOCKED"
    assert result["github_credentials_absent"] is True
