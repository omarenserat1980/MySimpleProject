from pathlib import Path


def test_termux_executor_install_contract_is_brain_only():
    root = Path(__file__).resolve().parents[1]
    script = (root / "brain_v12/local_worker/install_brain_executor.sh").read_text()
    assert "BRAIN_EXECUTOR_INSTALL_VERIFIED" in script
    assert "runner_policy=BRAIN_ONLY" in script
    assert "github_hosted_fallback=FORBIDDEN" in script
    assert "bootstrap_brain_executor.py" in script
