"""Read-only GitHub Actions runtime audit with a fail-closed CI exit code."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from brain_v12.github_control_plane import GitHubControlPlane

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / ".brain" / "state" / "github_actions_runtime_audit.json"
CRITICAL_CONCLUSIONS = {"failure", "timed_out", "action_required", "startup_failure"}
SAFE_ERROR_CODES = {
    "GITHUB_REPOSITORY_MISSING_OR_INVALID",
    "GITHUB_TOKEN_NOT_CONFIGURED",
    "WORKFLOW_INVENTORY_INCOMPLETE",
    "WORKFLOW_RUN_INVENTORY_INCOMPLETE",
    "WORKFLOW_AUDIT_INVALID_SNAPSHOT",
    "WORKFLOW_RUN_RECORD_INVALID",
    "GITHUB_HTTP_400",
    "GITHUB_HTTP_401",
    "GITHUB_HTTP_403",
    "GITHUB_HTTP_404",
    "GITHUB_HTTP_409",
    "GITHUB_HTTP_422",
    "GITHUB_HTTP_429",
    "GITHUB_HTTP_500",
    "GITHUB_HTTP_502",
    "GITHUB_HTTP_503",
    "GITHUB_NETWORK_ERROR",
    "ACTIONS_WORKFLOWS_INVALID_RESPONSE",
    "ACTIONS_WORKFLOWS_PAGINATION_LIMIT_REACHED",
    "ACTIONS_RUNS_INVALID_RESPONSE",
    "ACTIONS_RUNS_TOTAL_COUNT_MISSING",
    "ACTIONS_RUNS_API_RESULT_CAP_EXCEEDED",
    "ACTIONS_RUN_TIMESTAMP_MISSING",
    "ACTIONS_RUN_TIMESTAMP_INVALID",
    "ACTIONS_RUN_TIMESTAMP_TIMEZONE_MISSING",
    "ACTIONS_RUNS_PAGINATION_INCOMPLETE",
    "ACTIONS_RUNS_PAGINATION_LIMIT_REACHED",
}


def safe_error_code(exc: Exception) -> str:
    """Return an allowlisted code only; never copy exception text into evidence."""
    message = str(exc)
    candidate = message.split(":", 1)[0].splitlines()[0] if message else ""
    if candidate in SAFE_ERROR_CODES:
        return candidate
    return type(exc).__name__


def build_report(workflows_result: dict[str, Any], runs_result: dict[str, Any]) -> dict[str, Any]:
    """Convert complete API snapshots into an explicit audit result."""
    if workflows_result.get("complete") is not True:
        raise ValueError("WORKFLOW_INVENTORY_INCOMPLETE")
    if runs_result.get("complete") is not True:
        raise ValueError("WORKFLOW_RUN_INVENTORY_INCOMPLETE")
    workflows = workflows_result.get("workflows")
    runs = runs_result.get("workflow_runs")
    if not isinstance(workflows, list) or not isinstance(runs, list):
        raise ValueError("WORKFLOW_AUDIT_INVALID_SNAPSHOT")

    critical = []
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError("WORKFLOW_RUN_RECORD_INVALID")
        conclusion = run.get("conclusion")
        if isinstance(conclusion, str) and conclusion.lower() in CRITICAL_CONCLUSIONS:
            critical.append({
                "run_id": run.get("id"),
                "name": run.get("name"),
                "workflow_path": run.get("path"),
                "conclusion": conclusion.lower(),
                "html_url": run.get("html_url"),
                "created_at": run.get("created_at"),
            })
    return {
        "schema": "brain.github-actions-runtime-audit.v1",
        "status": "CRITICAL_WARN" if critical else "AUDITED",
        "complete": True,
        "workflow_count": len(workflows),
        "run_count_last_24h": len(runs),
        "critical_warning_count": len(critical),
        "critical_warnings": critical,
        "window": {
            "start": runs_result.get("window_start"),
            "end": runs_result.get("window_end"),
        },
        "policy": "Incomplete evidence fails closed; critical run conclusions produce a non-zero exit.",
    }


def main() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    repo = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    try:
        if "/" not in repo or not all(repo.split("/", 1)):
            raise ValueError("GITHUB_REPOSITORY_MISSING_OR_INVALID")
        if not token:
            raise ValueError("GITHUB_TOKEN_NOT_CONFIGURED")
        api = GitHubControlPlane(token=token)
        owner, name = repo.split("/", 1)
        workflows = api.actions_workflows_all(owner, name)
        runs = api.actions_runs_last_24h(owner, name)
        report = build_report(workflows, runs)
    except Exception as exc:
        report = {
            "schema": "brain.github-actions-runtime-audit.v1",
            "status": "AUDIT_BLOCKED",
            "complete": False,
            "critical_warning_count": None,
            "error_code": safe_error_code(exc),
            "policy": "Missing or incomplete audit evidence is a failure, never a pass.",
        }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("GITHUB_ACTIONS_AUDIT_STATUS=" + str(report["status"]))
    print("GITHUB_ACTIONS_AUDIT_COMPLETE=" + str(report["complete"]).lower())
    print("GITHUB_ACTIONS_CRITICAL_WARNINGS=" + str(report.get("critical_warning_count")))
    print("GITHUB_ACTIONS_AUDIT_EVIDENCE=" + str(REPORT_PATH.relative_to(ROOT)))
    return 0 if report["status"] == "AUDITED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
