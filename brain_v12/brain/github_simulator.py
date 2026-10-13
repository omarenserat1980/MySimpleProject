"""Deterministic, in-memory GitHub workflow simulator for Electronic Brain V12.

This module never calls GitHub, creates real repositories, pushes commits, runs hosted
Actions, reads credentials, or changes external state. All objects live in memory and
are intended for planning, tests, and dry-run evidence only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any


class GitHubSimulationError(ValueError):
    """Raised when a simulated GitHub operation violates the model."""


@dataclass
class SimulatedBranch:
    name: str
    files: dict[str, str] = field(default_factory=dict)
    commits: list[str] = field(default_factory=list)


@dataclass
class SimulatedPullRequest:
    number: int
    title: str
    head: str
    base: str
    state: str = "open"
    draft: bool = True
    merged: bool = False


class BrainGitHubSimulator:
    """Model a small, isolated subset of GitHub repository and CI workflows."""

    def __init__(self, repository: str = "example/brain-sandbox") -> None:
        if not repository or "/" not in repository:
            raise GitHubSimulationError("SIM_REPOSITORY_NAME_INVALID")
        self.repository = repository
        self.branches: dict[str, SimulatedBranch] = {
            "main": SimulatedBranch("main", {"README.md": "# Simulated repository\n"}, [])
        }
        self.pull_requests: dict[int, SimulatedPullRequest] = {}
        self.workflow_runs: list[dict[str, Any]] = []
        self._next_pr = 1

    @staticmethod
    def _digest(payload: str) -> str:
        return sha256(payload.encode("utf-8")).hexdigest()

    def create_branch(self, name: str, from_branch: str = "main") -> dict[str, Any]:
        if not name or name in self.branches:
            raise GitHubSimulationError("SIM_BRANCH_NAME_INVALID_OR_EXISTS")
        source = self.branches.get(from_branch)
        if source is None:
            raise GitHubSimulationError("SIM_BASE_BRANCH_NOT_FOUND")
        self.branches[name] = SimulatedBranch(name, dict(source.files), list(source.commits))
        return {"ok": True, "simulated": True, "branch": name, "from": from_branch}

    def commit_file(self, branch: str, path: str, content: str, message: str) -> dict[str, Any]:
        target = self.branches.get(branch)
        if target is None:
            raise GitHubSimulationError("SIM_BRANCH_NOT_FOUND")
        if not path or path.startswith("/") or ".." in path.split("/") or not message:
            raise GitHubSimulationError("SIM_FILE_PATH_OR_MESSAGE_INVALID")
        if not isinstance(content, str):
            raise GitHubSimulationError("SIM_FILE_CONTENT_MUST_BE_TEXT")
        digest = self._digest(f"{branch}\0{message}\0{path}\0{content}\0{len(target.commits)}")
        target.files[path] = content
        target.commits.append(digest)
        return {"ok": True, "simulated": True, "commit": digest, "branch": branch, "path": path}

    def open_pull_request(
        self, title: str, head: str, base: str = "main", draft: bool = True
    ) -> dict[str, Any]:
        if not title or head == base or head not in self.branches or base not in self.branches:
            raise GitHubSimulationError("SIM_PULL_REQUEST_INPUT_INVALID")
        number = self._next_pr
        self._next_pr += 1
        pr = SimulatedPullRequest(number, title, head, base, draft=draft)
        self.pull_requests[number] = pr
        return {"ok": True, "simulated": True, **pr.__dict__}

    def run_workflow(self, name: str, branch: str, checks: dict[str, bool]) -> dict[str, Any]:
        if not name or branch not in self.branches or not checks:
            raise GitHubSimulationError("SIM_WORKFLOW_INPUT_INVALID")
        normalized = {str(key): bool(value) for key, value in checks.items()}
        conclusion = "success" if all(normalized.values()) else "failure"
        run = {
            "run_number": len(self.workflow_runs) + 1,
            "workflow": name,
            "branch": branch,
            "status": "completed",
            "conclusion": conclusion,
            "checks": normalized,
            "simulated": True,
            "hosted_github_actions": False,
        }
        self.workflow_runs.append(run)
        return dict(run)

    def snapshot(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "mode": "SIMULATION_ONLY",
            "external_github_calls": False,
            "credentials_read": False,
            "real_commits_created": False,
            "real_pull_requests_created": False,
            "hosted_workflows_run": False,
            "branches": {
                name: {"file_count": len(branch.files), "commit_count": len(branch.commits)}
                for name, branch in sorted(self.branches.items())
            },
            "pull_request_count": len(self.pull_requests),
            "workflow_run_count": len(self.workflow_runs),
        }


def self_test() -> dict[str, Any]:
    """Run a tiny deterministic scenario and return machine-readable evidence."""
    sim = BrainGitHubSimulator()
    sim.create_branch("feature/demo")
    sim.commit_file("feature/demo", "demo.txt", "hello brain\n", "Add demo")
    pr = sim.open_pull_request("Demo change", "feature/demo")
    run = sim.run_workflow("brain-simulator-ci", "feature/demo", {"unit_tests": True, "lint": True})
    return {
        "ok": pr["simulated"] and run["conclusion"] == "success",
        "scenario": "branch_commit_draft_pr_simulated_ci",
        "pr_number": pr["number"],
        "workflow_conclusion": run["conclusion"],
        "snapshot": sim.snapshot(),
    }
