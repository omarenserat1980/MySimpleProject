from pathlib import Path

WINDOWS_WORKFLOW = Path(".github/workflows/brain-windows-real-boot.yml")
INTERNAL_RUNTIME_WORKFLOW = Path(".github/workflows/brain-github-cloud.yml")
SUPERVISOR_WORKFLOW = Path(".github/workflows/brain-supervisor.yml")
REQUIRED_LABELS = ("self-hosted", "linux", "x64", "brain-internal", "qemu", "windows-real-boot")


def test_windows_real_boot_never_uses_github_hosted_runner():
    text = WINDOWS_WORKFLOW.read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" not in text
    line = next(line.strip() for line in text.splitlines() if line.strip().startswith("runs-on:"))
    for label in REQUIRED_LABELS:
        assert label in line, (label, line)


def test_windows_real_boot_has_fail_closed_preflight():
    text = WINDOWS_WORKFLOW.read_text(encoding="utf-8")
    assert "BRAIN_INTERNAL_RUNNER_FLAG" in text
    assert "BRAIN_INTERNAL_RUNNER=VERIFIED" in text
    assert "internal_runner_preflight" in text



def test_internal_runtime_never_uses_github_hosted_runner():
    text = INTERNAL_RUNTIME_WORKFLOW.read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" not in text
    assert "self-hosted" in text
    assert "brain-internal" in text
    assert "BRAIN_INTERNAL_RUNNER_FLAG" in text
    assert "internal_runner_preflight" in text
    assert '"github_hosted_runtime":false' in text


def test_supervisor_does_not_dispatch_github_hosted_runtime():
    text = SUPERVISOR_WORKFLOW.read_text(encoding="utf-8")
    assert "brain-github-cloud.yml/dispatches" not in text
    assert "runs-on: ubuntu-latest" not in text.split("dispatch_internal_task:", 1)[1].split("health_and_recovery:", 1)[0]
    assert "brain-internal" in text
