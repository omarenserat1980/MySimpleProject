from brain_v12.self_healing.supervisor import diagnose


def test_diagnose_missing_token():
    assert "missing-token" in diagnose("", "GITHUB_TOKEN_REQUIRED", 2)


def test_diagnose_syntax():
    assert "syntax" in diagnose("", "SyntaxError: invalid syntax", 1)


def test_diagnose_network():
    assert "network" in diagnose("", "Connection reset by peer", 1)
