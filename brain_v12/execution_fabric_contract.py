"""Contract gate for the Brain Execution Fabric.

This gate is intentionally static and fail-closed. It protects the invariant
that production execution belongs to Brain-owned runtime layers.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_WORKFLOWS = (
    ".github/workflows/brain-github-cloud.yml",
    ".github/workflows/brain-120-minute-cinema.yml",
    ".github/workflows/brain-three-films-factory.yml",
    ".github/workflows/brain-local-cinema-smoke.yml",
    ".github/workflows/brain-continuous-self-healing.yml",
    ".github/workflows/brain-human-intermediary-autopilot.yml",
    ".github/workflows/brain-supervisor.yml",
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

    fabric = ROOT / "brain_v12/brain/execution_fabric.py"
    gateway = ROOT / "brain_v12/brain/execution_gateway.py"
    runtime = ROOT / "brain_v12/brain/internal_task_runtime.py"

    for path in (fabric, gateway, runtime):
        if not path.exists():
            failures.append(f"MISSING_EXECUTION_COMPONENT:{path}")

    if gateway.exists():
        gateway_text = gateway.read_text(encoding="utf-8")
        if "BrainExecutionGateway" not in gateway_text:
            failures.append("GATEWAY_CLASS_MISSING")
        if "github" in gateway_text.lower() and "fallback" in gateway_text.lower():
            failures.append("GATEWAY_EXTERNAL_FALLBACK_MARKER")

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
