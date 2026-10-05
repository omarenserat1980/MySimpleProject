from pathlib import Path

WORKFLOW = Path(".github/workflows/brain-windows-real-boot.yml")
REQUIRED_LABELS = ("self-hosted", "linux", "x64", "brain-internal", "qemu", "windows-real-boot")


def test_windows_real_boot_never_uses_github_hosted_runner():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" not in text
    line = next(line.strip() for line in text.splitlines() if line.strip().startswith("runs-on:"))
    for label in REQUIRED_LABELS:
        assert label in line, (label, line)


def test_windows_real_boot_has_fail_closed_preflight():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "BRAIN_INTERNAL_RUNNER_FLAG" in text
    assert "BRAIN_INTERNAL_RUNNER=VERIFIED" in text
    assert "internal_runner_preflight" in text
