"""Contract gate for the Brain Execution Fabric.

This gate is intentionally static and fail-closed. It protects the invariant
that production execution belongs to Brain-owned runtime layers.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_WORKFLOWS = (
    ".github/workflows/brain-continuous-self-healing.yml",
)

FORBIDDEN_RUNTIME_MARKERS = (
    "runs-on: ubuntu-latest",
    "runs-on: ubuntu-24.04",
    "runs-on: ubuntu-22.04",
)

REQUIRED_RUNTIME_MARKERS = (
    "brain-internal",
    "internal_runner_preflight",
)


def assert_runtime_contract() -> dict:
    failures: list[str] = []
    checked: list[str] = []

    for relative in RUNTIME_WORKFLOWS:
        path = ROOT / relative
        checked.append(relative)
        if not path.exists():
            failures.append(f"MISSING_RUNTIME_WORKFLOW:{relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_RUNTIME_MARKERS:
            if marker in text:
                failures.append(f"FORBIDDEN_MARKER:{relative}:{marker}")
        for marker in REQUIRED_RUNTIME_MARKERS:
            if marker not in text:
                failures.append(f"REQUIRED_MARKER_MISSING:{relative}:{marker}")

    # Allowlisted unit-test/health tasks are safe on hosted infrastructure.
    # Privileged supervisor repair remains in the separate protected workflow.
    cloud_path = ROOT / ".github/workflows/brain-github-cloud.yml"
    if cloud_path.exists():
        cloud_text = cloud_path.read_text(encoding="utf-8")
        if "runs-on: ubuntu-latest" not in cloud_text:
            failures.append("BRAIN_SOFTWARE_RUNTIME_NOT_HOSTED")
        if "self-hosted" in cloud_text or "internal_runner_preflight" in cloud_text:
            failures.append("BRAIN_SOFTWARE_RUNTIME_REQUIRES_INTERNAL_RUNNER")
        if "BRAIN_EXECUTION_MODE: GITHUB_HOSTED_SOFTWARE" not in cloud_text:
            failures.append("BRAIN_SOFTWARE_RUNTIME_MODE_MISSING")
        if "github_hosted_runtime\\\": True" not in cloud_text:
            failures.append("BRAIN_SOFTWARE_RUNTIME_EVIDENCE_MARKER_MISSING")
        if "contents: write" in cloud_text:
            failures.append("BRAIN_SOFTWARE_RUNTIME_HAS_WRITE_PERMISSION")
        task_runner = ROOT / "brain_v12/ci/brain_runner.py"
        if not task_runner.exists():
            failures.append("BRAIN_ALLOWLISTED_TASK_RUNNER_MISSING")
        else:
            runner_text = task_runner.read_text(encoding="utf-8")
            for marker in ("TASKS = {", "REJECTED_TASK", "if command is None"):
                if marker not in runner_text:
                    failures.append(f"BRAIN_ALLOWLISTED_TASK_CONTRACT_MISSING:{marker}")
    else:
        failures.append("MISSING_BRAIN_SOFTWARE_RUNTIME_WORKFLOW")

    # The human-intermediary predictor is bounded state/evidence work, not
    # production execution; it is safe to run on GitHub-hosted infrastructure.
    autopilot_path = ROOT / ".github/workflows/brain-human-intermediary-autopilot.yml"
    if autopilot_path.exists():
        autopilot_text = autopilot_path.read_text(encoding="utf-8")
        if "runs-on: ubuntu-latest" not in autopilot_text:
            failures.append("HUMAN_INTERMEDIARY_AUTOPILOT_NOT_HOSTED")
        if "RUNNER_ENVIRONMENT" not in autopilot_text:
            failures.append("HUMAN_INTERMEDIARY_AUTOPILOT_HOSTED_GUARD_MISSING")
        if "internal_runner_preflight" in autopilot_text:
            failures.append("HUMAN_INTERMEDIARY_AUTOPILOT_REQUIRES_INTERNAL_RUNNER")
        for marker in (
            "automatic_production_code_mutation",
            "automatic_financial_or_external_side_effects",
            "success_requires_evidence",
        ):
            if marker not in autopilot_text:
                failures.append(f"HUMAN_INTERMEDIARY_AUTOPILOT_SAFETY_CONTRACT_MISSING:{marker}")
    else:
        failures.append("MISSING_HUMAN_INTERMEDIARY_AUTOPILOT")

    # The long-form cinema pipeline is software rendering, not real guest boot.
    cinema_path = ROOT / ".github/workflows/brain-120-minute-cinema.yml"
    if cinema_path.exists():
        cinema_text = cinema_path.read_text(encoding="utf-8")
        if cinema_text.count("runs-on: ubuntu-latest") != 2:
            failures.append("120_MINUTE_CINEMA_NOT_HOSTED")
        if "internal_runner_preflight" in cinema_text:
            failures.append("120_MINUTE_CINEMA_REQUIRES_INTERNAL_RUNNER")
    else:
        failures.append("MISSING_120_MINUTE_CINEMA_WORKFLOW")

    # ISO creation plus QEMU emulation is hosted software verification, not physical boot.
    iso_path = ROOT / ".github/workflows/brain-boot-iso.yml"
    if iso_path.exists():
        iso_text = iso_path.read_text(encoding="utf-8")
        if "runs-on: ubuntu-latest" not in iso_text:
            failures.append("BRAIN_ISO_QEMU_NOT_HOSTED")
        if "self-hosted" in iso_text or "BRAIN_INTERNAL_RUNNER_FLAG" in iso_text:
            failures.append("BRAIN_ISO_QEMU_REQUIRES_INTERNAL_RUNNER")
        for package in ("grub-pc-bin", "xorriso", "gcc", "qemu-system-x86"):
            if package not in iso_text:
                failures.append(f"BRAIN_ISO_TOOLCHAIN_PACKAGE_MISSING:{package}")
    else:
        failures.append("MISSING_BRAIN_ISO_WORKFLOW")

    # The three-film renderer is software-only; real boot stays separately gated.
    three_films_path = ROOT / ".github/workflows/brain-three-films-factory.yml"
    if three_films_path.exists():
        three_films_text = three_films_path.read_text(encoding="utf-8")
        if "runs-on: ubuntu-latest" not in three_films_text:
            failures.append("THREE_FILMS_FACTORY_NOT_HOSTED")
        if "internal_runner_preflight" in three_films_text:
            failures.append("THREE_FILMS_FACTORY_REQUIRES_INTERNAL_RUNNER")
    else:
        failures.append("MISSING_THREE_FILMS_FACTORY_WORKFLOW")

    # Hardware-independent verification jobs must run on GitHub-hosted runners.
    supervisor_path = ROOT / ".github/workflows/brain-supervisor.yml"
    cinema_smoke_path = ROOT / ".github/workflows/brain-local-cinema-smoke.yml"
    if supervisor_path.exists():
        supervisor_text = supervisor_path.read_text(encoding="utf-8")
        for job_name, next_job in (("health_and_recovery", "self_heal"), ("verify", None)):
            start = supervisor_text.find(f"  {job_name}:")
            end = supervisor_text.find(f"\n  {next_job}:", start) if next_job else len(supervisor_text)
            if start < 0 or end < 0:
                failures.append(f"SUPERVISOR_JOB_MISSING:{job_name}")
                continue
            job_text = supervisor_text[start:end]
            if "runs-on: ubuntu-latest" not in job_text:
                failures.append(f"SIMULATION_JOB_NOT_HOSTED:{job_name}")
            if "internal_runner_preflight" in job_text:
                failures.append(f"SIMULATION_JOB_REQUIRES_INTERNAL_HARDWARE:{job_name}")
        dispatch_start = supervisor_text.find("  dispatch_internal_task:")
        dispatch_end = supervisor_text.find("\n  health_and_recovery:", dispatch_start)
        dispatch = supervisor_text[dispatch_start:dispatch_end] if dispatch_start >= 0 and dispatch_end >= 0 else ""
        if "self-hosted" not in dispatch or "internal_runner_preflight" not in dispatch:
            failures.append("INTERNAL_TASK_DISPATCH_GUARD_MISSING")
    else:
        failures.append("MISSING_SUPERVISOR_WORKFLOW")
    if cinema_smoke_path.exists():
        cinema_text = cinema_smoke_path.read_text(encoding="utf-8")
        if "runs-on: ubuntu-latest" not in cinema_text:
            failures.append("LOCAL_CINEMA_SMOKE_NOT_HOSTED")
        if "internal_runner_preflight" in cinema_text:
            failures.append("LOCAL_CINEMA_SMOKE_REQUIRES_INTERNAL_RUNNER")
    else:
        failures.append("MISSING_LOCAL_CINEMA_SMOKE_WORKFLOW")

    fabric = ROOT / "brain_v12/brain/execution_fabric.py"
    gateway = ROOT / "brain_v12/brain/execution_gateway.py"
    runtime = ROOT / "brain_v12/brain/internal_task_runtime.py"
    problem_solver = ROOT / "brain_v12/brain/problem_solver.py"

    for path in (fabric, gateway, runtime, problem_solver):
        if not path.exists():
            failures.append(f"MISSING_EXECUTION_COMPONENT:{path}")

    if gateway.exists():
        gateway_text = gateway.read_text(encoding="utf-8")
        if "BrainExecutionGateway" not in gateway_text:
            failures.append("GATEWAY_CLASS_MISSING")
        if "github" in gateway_text.lower() and "fallback" in gateway_text.lower():
            failures.append("GATEWAY_EXTERNAL_FALLBACK_MARKER")

    if problem_solver.exists():
        solver_text = problem_solver.read_text(encoding="utf-8")
        if "self.execution_gateway" not in solver_text:
            failures.append("PROBLEM_SOLVER_GATEWAY_MISSING")
        if "EXTERNAL_ALTERNATIVE_EXECUTOR_FORBIDDEN" not in solver_text:
            failures.append("PROBLEM_SOLVER_EXTERNAL_EXECUTOR_GUARD_MISSING")

    if fabric.exists():
        fabric_text = fabric.read_text(encoding="utf-8")
        if "EXTERNAL_WORKER_FORBIDDEN" not in fabric_text:
            failures.append("EXTERNAL_WORKER_GUARD_MISSING")

    result = {
        "contract": "BRAIN_EXECUTION_FABRIC",
        "checked_workflows": checked,
        "failures": failures,
        "verified": not failures,
    }
    if failures:
        raise RuntimeError("BRAIN_EXECUTION_FABRIC_CONTRACT_FAILED:" + ";".join(failures))
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(assert_runtime_contract(), indent=2))
