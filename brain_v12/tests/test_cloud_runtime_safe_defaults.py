"""Regression checks for safe Brain Cloud runtime defaults."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cloud_worker_has_no_implicit_render_origin():
    source = (ROOT / "brain_v12" / "cloud_worker_service.py").read_text(encoding="utf-8")
    entrypoint = (ROOT / "brain_v12" / "container_entrypoint.py").read_text(encoding="utf-8")
    assert "onrender.com" not in source
    assert "onrender.com" not in entrypoint
    assert 'os.getenv("BRAIN_ORIGIN", "")' in source


def test_runtime_launcher_does_not_self_assert_trust():
    source = (ROOT / "tools" / "run_brain_cloud_runtime.sh").read_text(encoding="utf-8")
    assert "export BRAIN_INTERNAL_RUNNER_FLAG=1" not in source
    assert ': "${BRAIN_INTERNAL_RUNNER_FLAG:?Set BRAIN_INTERNAL_RUNNER_FLAG' in source


def test_example_env_does_not_enable_trusted_runner_by_default():
    source = (ROOT / "cloud" / "brain-cloud.env.example").read_text(encoding="utf-8")
    assert "\nBRAIN_INTERNAL_RUNNER_FLAG=1\n" not in source
    assert "provisioned out-of-band" in source
