from brain_v12.self_healing.supervisor import diagnose


def test_diagnose_missing_token():
    assert "missing-token" in diagnose("", "GITHUB_TOKEN_REQUIRED", 2)


def test_diagnose_syntax():
    assert "syntax" in diagnose("", "SyntaxError: invalid syntax", 1)


def test_diagnose_network():
    assert "network" in diagnose("", "Connection reset by peer", 1)


def test_workflow_actions_disabled_by_default(monkeypatch):
    monkeypatch.delenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", raising=False)
    from brain_v12.self_healing.supervisor import workflow_actions_enabled
    assert workflow_actions_enabled() is False


def test_workflow_actions_require_explicit_opt_in():
    from brain_v12.self_healing.supervisor import workflow_actions_enabled
    assert workflow_actions_enabled("1") is True
    assert workflow_actions_enabled("true") is True
    assert workflow_actions_enabled("yes") is True
    assert workflow_actions_enabled("0") is False
    assert workflow_actions_enabled("false") is False
    assert workflow_actions_enabled("anything") is False


def test_workflow_actions_environment_value_is_normalized(monkeypatch):
    from brain_v12.self_healing.supervisor import workflow_actions_enabled

    monkeypatch.setenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", " TRUE ")
    assert workflow_actions_enabled() is True

    monkeypatch.setenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", " YES ")
    assert workflow_actions_enabled() is True

    monkeypatch.setenv("BRAIN_ENABLE_WORKFLOW_ACTIONS", "on")
    assert workflow_actions_enabled() is False
