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


def test_supervisor_keeps_task_dispatch_on_brain_owned_runtime():
    text = SUPERVISOR_WORKFLOW.read_text(encoding="utf-8")
    dispatch = text.split("dispatch_internal_task:", 1)[1].split("health_and_recovery:", 1)[0]
    assert "brain-github-cloud.yml/dispatches" not in text
    assert "self-hosted" in dispatch
    assert "brain-internal" in dispatch
    assert "internal_runner_preflight" in dispatch


def test_supervisor_simulation_and_verification_use_hosted_runner():
    text = SUPERVISOR_WORKFLOW.read_text(encoding="utf-8")
    health = text.split("health_and_recovery:", 1)[1].split("self_heal:", 1)[0]
    verify = text.split("verify:", 1)[1]
    for job in (health, verify):
        assert "runs-on: ubuntu-latest" in job
        assert "internal_runner_preflight" not in job


RUNTIME_WORKFLOWS = (
    Path(".github/workflows/brain-github-cloud.yml"),
    Path(".github/workflows/brain-local-cinema-smoke.yml"),
    Path(".github/workflows/brain-continuous-self-healing.yml"),
    Path(".github/workflows/brain-supervisor.yml"),
)


def test_remaining_runtime_workloads_are_brain_owned():
    # These still perform internal task execution or bounded autonomous repair.
    # Migrate them separately; hosted-runner simulation jobs are classified above.
    remaining = tuple(
        workflow for workflow in RUNTIME_WORKFLOWS
        if workflow.name not in {"brain-local-cinema-smoke.yml", "brain-supervisor.yml"}
    )
    for workflow in remaining:
        text = workflow.read_text(encoding="utf-8")
        assert "runs-on: ubuntu-latest" not in text, workflow
        assert "brain-internal" in text, workflow
        assert "internal_runner_preflight" in text, workflow


def test_human_intermediary_autopilot_uses_hosted_runner_for_bounded_state_only():
    text = Path(".github/workflows/brain-human-intermediary-autopilot.yml").read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" in text
    assert "RUNNER_ENVIRONMENT" in text
    assert "BRAIN_EXECUTION_MODE=GITHUB_HOSTED_SOFTWARE" in text
    assert "internal_runner_preflight" not in text
    assert '"automatic_production_code_mutation": False' in text
    assert '"automatic_financial_or_external_side_effects": False' in text


def test_brain_iso_qemu_verification_uses_hosted_runner():
    text = Path(".github/workflows/brain-boot-iso.yml").read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" in text
    assert "self-hosted" not in text
    assert "BRAIN_INTERNAL_RUNNER_FLAG" not in text
    assert "qemu-system-x86" in text
    assert "Boot ISO with QEMU" in text


def test_120_minute_cinema_uses_hosted_software_runners():
    text = Path(".github/workflows/brain-120-minute-cinema.yml").read_text(encoding="utf-8")
    assert text.count("runs-on: ubuntu-latest") == 2
    assert "internal_runner_preflight" not in text
    assert "name: Render shard" in text
    assert "name: Assemble and verify cinematic master" in text


def test_three_films_factory_is_hardware_independent():
    text = Path(".github/workflows/brain-three-films-factory.yml").read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" in text
    assert "internal_runner_preflight" not in text
    assert "Build three original masters" in text


def test_local_cinema_smoke_is_hardware_independent():
    text = Path(".github/workflows/brain-local-cinema-smoke.yml").read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" in text
    assert "internal_runner_preflight" not in text
    assert "BRAIN_LOCAL_PAINTER_SMOKE=VERIFIED" in text


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



def test_v12_orchestrator_ownership_boundary_is_explicit():
    v12 = Path("brain_v12/brain/orchestrator.py").read_text(encoding="utf-8")
    app = Path("brain_v12/app.py").read_text(encoding="utf-8")
    v7 = Path("brain_v7/braincore_v2/cognitive_orchestrator.py").read_text(encoding="utf-8")
    autonomous = Path("brain_v12/brain/autonomous_supervisor.py").read_text(encoding="utf-8")

    assert "class CognitiveOrchestrator" in v12
    assert "CognitiveOrchestrator" in app
    assert "class CognitiveOrchestrator" in v7  # legacy remains frozen
    assert "BrainAutonomousSupervisor" in autonomous
    assert "BrainSupervisor" not in autonomous
