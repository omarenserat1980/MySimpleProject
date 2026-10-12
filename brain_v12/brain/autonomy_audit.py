"""Reproducible audit of GitHub Actions runner independence.

This reports runner placement, not total system autonomy. A hosted runner does
not prove a task is behaviorally autonomous, and modeled resources are not real
hardware. Unknown runner expressions are counted conservatively as unresolved.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
JOB_HEADER = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(?:#.*)?$")
HOSTED_MARKERS = (
    "ubuntu-latest", "ubuntu-24.04", "ubuntu-22.04",
    "windows-latest", "windows-2022", "windows-2019",
    "macos-latest", "macos-14", "macos-13",
)
# These workflows deliberately verify capabilities that cannot honestly be
# certified by a generic hosted software runner. They remain visible in the
# all-jobs score, but are excluded from the optional software-scope comparison.
HARDWARE_SPECIFIC_WORKFLOWS = {
    "brain-windows-real-boot.yml",
    "brain-windows-real-boot-dependency-gate.yml",
    "windows-real-boot-runner-diagnostic.yml",
    "arkan-readonly-hyperv-preflight.yml",
}


def _runner_for_job(job_text: str) -> tuple[str, str | None]:
    for line in job_text.splitlines():
        match = re.match(r"^\s{4}runs-on:\s*(.*?)\s*$", line)
        if not match:
            continue
        value = match.group(1).strip().strip("'\"")
        lowered = value.lower()
        if "self-hosted" in lowered:
            return "self_hosted", value
        if any(marker in lowered for marker in HOSTED_MARKERS):
            return "github_hosted", value
        if "${{" in value:
            return "dynamic_unresolved", value
        return "unknown", value
    return "missing", None


def _jobs_in_workflow(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    jobs_index = next((i for i, line in enumerate(lines) if line.strip() == "jobs:" and not line.startswith(" ")), None)
    if jobs_index is None:
        return []
    starts: list[tuple[int, str]] = []
    for i in range(jobs_index + 1, len(lines)):
        line = lines[i]
        if line and not line.startswith(" "):
            break
        match = JOB_HEADER.match(line)
        if match:
            starts.append((i, match.group(1)))
    found = []
    for index, (start, name) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        state, expression = _runner_for_job("\n".join(lines[start:end]))
        found.append({
            "workflow": path.name,
            "job": name,
            "runner_class": state,
            "runs_on": expression,
            "hardware_specific_workflow": path.name in HARDWARE_SPECIFIC_WORKFLOWS,
        })
    return found


def calculate_audit(workflow_root: str | Path = WORKFLOW_ROOT) -> dict[str, Any]:
    root = Path(workflow_root)
    if not root.exists():
        raise FileNotFoundError(f"WORKFLOW_ROOT_NOT_FOUND:{root}")
    files = sorted(p for p in root.rglob("*.yml") if p.is_file())
    files += sorted(p for p in root.rglob("*.yaml") if p.is_file())
    jobs = [job for path in files for job in _jobs_in_workflow(path)]
    if not jobs:
        raise RuntimeError("NO_WORKFLOW_JOBS_DISCOVERED")

    def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
        counts = {key: sum(1 for item in items if item["runner_class"] == key)
                  for key in ("github_hosted", "self_hosted", "dynamic_unresolved", "unknown", "missing")}
        total = len(items)
        counts["total_jobs"] = total
        counts["runner_independence_percent"] = round(100 * counts["github_hosted"] / total, 2) if total else 0.0
        counts["resolved_runner_percent"] = round(100 * (counts["github_hosted"] + counts["self_hosted"]) / total, 2) if total else 0.0
        return counts

    software_jobs = [j for j in jobs if not j["hardware_specific_workflow"]]
    return {
        "schema": "brain.runner-independence-audit.v1",
        "method": "static workflow/job inventory; hosted runner share only",
        "workflow_count": len(files),
        "job_count": len(jobs),
        "all_workflows": summarize(jobs),
        "software_scope_excluding_explicit_hardware_verification": summarize(software_jobs),
        "hardware_specific_workflows_excluded_from_software_scope": sorted(HARDWARE_SPECIFIC_WORKFLOWS),
        "unresolved_jobs": [j for j in jobs if j["runner_class"] in {"dynamic_unresolved", "unknown", "missing"}],
        "self_hosted_jobs": [j for j in jobs if j["runner_class"] == "self_hosted"],
        "full_autonomy_certified": False,
        "limitations": [
            "This is a runner-placement index, not a complete autonomy percentage.",
            "A GitHub-hosted job can still require secrets, external services, or manual approval.",
            "Self-hosted jobs are counted as hardware/runner dependencies even if their host might be virtual.",
            "Hardware-specific verification is excluded only from the software-scope comparison, never from the all-workflows view.",
            "Behavioral execution, recovery, security boundaries, and artifact evidence require separate tests.",
        ],
    }


def main() -> int:
    result = calculate_audit()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
