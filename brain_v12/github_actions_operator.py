"""Governed GitHub Actions operator for Electronic Brain.

Uses GitHub REST directly, requires explicit approval for dispatch, polls for
the resulting run, and never treats an accepted dispatch as verified success.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any

from .github_control_plane import GitHubControlError, GitHubControlPlane


@dataclass(frozen=True)
class WorkflowEvidence:
    workflow: str
    run_id: int | None
    state: str
    conclusion: str | None
    verified: bool
    reason: str
    ref: str | None = None
    created_at: str | None = None
    run_url: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "workflow": self.workflow,
            "run_id": self.run_id,
            "state": self.state,
            "conclusion": self.conclusion,
            "verified": self.verified,
            "reason": self.reason,
            "ref": self.ref,
            "created_at": self.created_at,
            "run_url": self.run_url,
        }


class GitHubActionsOperator:
    def __init__(self, control_plane: GitHubControlPlane | None = None):
        self.github = control_plane or GitHubControlPlane()

    @staticmethod
    def _split_repo(repo_full_name: str) -> tuple[str, str]:
        parts = repo_full_name.strip("/").split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("INVALID_REPOSITORY:expected owner/name")
        return parts[0], parts[1]

    def dispatch(self, repo_full_name: str, workflow_id: str, *, ref: str = "main",
                 inputs: dict[str, str] | None = None, approved: bool = False) -> dict[str, Any]:
        owner, repo = self._split_repo(repo_full_name)
        self.github.dispatch_workflow(owner, repo, workflow_id, ref=ref,
                                      inputs=inputs, approved=approved)
        return {"state": "DISPATCH_ACCEPTED", "workflow": workflow_id, "ref": ref,
                "repository": repo_full_name, "verification": "PENDING_RUN_OBSERVATION"}

    def latest_run(self, repo_full_name: str, workflow_id: str | None = None) -> dict[str, Any] | None:
        owner, repo = self._split_repo(repo_full_name)
        data = self.github.actions_runs(owner, repo, page=1, per_page=50)
        runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
        if workflow_id:
            runs = [r for r in runs if str(r.get("path", "")).endswith(workflow_id)
                    or str(r.get("name", "")) == workflow_id
                    or str(r.get("workflow_id", "")) == workflow_id]
        if not runs:
            return None
        # GitHub normally returns newest-first, but sort explicitly so verification
        # never depends on an undocumented ordering assumption.
        return max(runs, key=lambda r: str(r.get("created_at", "")))

    def wait_for_run(self, repo_full_name: str, workflow_id: str, *,
                     timeout_seconds: int = 900, poll_seconds: int = 10,
                     not_before: float | None = None) -> WorkflowEvidence:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            run = self.latest_run(repo_full_name, workflow_id)
            if run and not_before is not None:
                created = run.get("created_at", "")
                try:
                    created_ts = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                except (ValueError, TypeError):
                    created_ts = 0.0
                if created_ts < not_before - 5:
                    run = None
            if run and run.get("status") == "completed":
                conclusion = run.get("conclusion")
                verified = conclusion == "success"
                return WorkflowEvidence(
                    workflow_id, run.get("id"), "VERIFIED" if verified else "FAILED",
                    conclusion, verified,
                    "completed_success" if verified else "workflow_conclusion_not_success",
                    ref=run.get("head_branch") or run.get("ref"),
                    created_at=run.get("created_at"),
                    run_url=run.get("html_url"),
                )
            time.sleep(max(1, poll_seconds))
        return WorkflowEvidence(workflow_id, None, "TIMEOUT", None, False,
                                "no_completed_run_observed_before_timeout")

    def dispatch_and_wait(self, repo_full_name: str, workflow_id: str, *,
                          ref: str = "main", inputs: dict[str, str] | None = None,
                          approved: bool = False, timeout_seconds: int = 900,
                          poll_seconds: int = 10) -> dict[str, Any]:
        not_before = time.time()
        dispatch = self.dispatch(repo_full_name, workflow_id, ref=ref, inputs=inputs, approved=approved)
        evidence = self.wait_for_run(repo_full_name, workflow_id,
                                     timeout_seconds=timeout_seconds, poll_seconds=poll_seconds,
                                     not_before=not_before)
        return {"dispatch": dispatch, "evidence": evidence.as_dict(),
                "verified_completed": evidence.verified}


__all__ = ["GitHubActionsOperator", "WorkflowEvidence", "GitHubControlError"]
