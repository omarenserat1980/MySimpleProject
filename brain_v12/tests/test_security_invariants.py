from pathlib import Path

def test_security_policy_is_present():
    assert Path("docs/BRAIN_SECURITY_HARDENING.md").is_file()
    assert Path("docs/BRAIN_DEFENSE_IN_DEPTH.md").is_file()

def test_security_workflow_is_read_only():
    text = Path(".github/workflows/brain-security-hardening.yml").read_text()
    assert "permissions:\n  contents: read" in text
    assert "write-token" not in text.lower()

def test_no_obvious_secret_material_in_security_docs():
    for path in (
        Path("docs/BRAIN_SECURITY_HARDENING.md"),
        Path("docs/BRAIN_DEFENSE_IN_DEPTH.md"),
    ):
        text = path.read_text().lower()
        assert "begin rsa private key" not in text
        assert "begin openssh private key" not in text
