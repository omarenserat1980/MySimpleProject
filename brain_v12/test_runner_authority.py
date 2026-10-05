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


RUNTIME_WORKFLOWS = (
    Path(".github/workflows/brain-github-cloud.yml"),
    Path(".github/workflows/brain-120-minute-cinema.yml"),
    Path(".github/workflows/brain-three-films-factory.yml"),
    Path(".github/workflows/brain-local-cinema-smoke.yml"),
    Path(".github/workflows/brain-continuous-self-healing.yml"),
    Path(".github/workflows/brain-human-intermediary-autopilot.yml"),
    Path(".github/workflows/brain-supervisor.yml"),
)


def test_runtime_workloads_are_brain_owned():
    for workflow in RUNTIME_WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        assert "runs-on: ubuntu-latest" not in text, workflow
        assert "brain-internal" in text, workflow
        assert "internal_runner_preflight" in text, workflow


def test_canonical_internal_runtime_modules_exist():
    gateway = Path("brain_v12/brain/execution_gateway.py")
    runtime = Path("brain_v12/brain/internal_task_runtime.py")
    assert gateway.exists()
    assert runtime.exists()
    assert "BrainExecutionGateway" in gateway.read_text(encoding="utf-8")
    assert "github_dependency" in runtime.read_text(encoding="utf-8")
def test_v12_supervisor_policy_has_single_canonical_owner():
    canonical = Path("brain_v12/brain/brain_supervisor.py")
    compatibility = Path("brain_v12/brain/supervisor.py")
    canonical_text = canonical.read_text(encoding="utf-8")
    compatibility_text = compatibility.read_text(encoding="utf-8")

    assert "class BrainSupervisor" in canonical_text
    assert "class BrainSupervisor" not in compatibility_text
    assert "from .brain_supervisor import BrainSupervisor" in compatibility_text
    assert "BrainSupervisor" in Path("brain_v12/app.py").read_text(encoding="utf-8")

