"""GitHub task lifecycle for Brain.

This layer models execution without pretending that a connected-tool response is
domain verification. It is safe to use for autonomous planning and retry logic.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .github_planner import GitHubPlanner, UnifiedGitHubPlan

STATES = ("PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED", "RETRYING")

@dataclass
class GitHubTask:
    intent: str
    state: str = "PENDING"
    attempts: int = 0
    evidence: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

class GitHubTaskEngine:
    def __init__(self, planner: GitHubPlanner | None = None):
        self.planner = planner or GitHubPlanner()

    def discover(self, intent: str) -> UnifiedGitHubPlan:
        return self.planner.plan(intent)

    def start(self, task: GitHubTask) -> GitHubTask:
        if task.state != "PENDING":
            raise ValueError(f"INVALID_TASK_STATE:{task.state}")
        task.state = "RUNNING"
        task.attempts += 1
        return task

    def record_transport_result(self, task: GitHubTask, tool: str, result: Any) -> GitHubTask:
        evidence = self.planner.executor.verify_envelope(tool, result)
        task.evidence.append(evidence)
        if evidence["verified"]:
            task.state = "SUCCESS"
            task.error = None
        else:
            task.state = "FAILED"
            task.error = "NO_TRANSPORT_RESULT"
        return task

    def retry(self, task: GitHubTask) -> GitHubTask:
        if task.state != "FAILED":
            raise ValueError(f"RETRY_REQUIRES_FAILED:{task.state}")
        task.state = "RETRYING"
        return task

    def fail(self, task: GitHubTask, error: str) -> GitHubTask:
        task.state = "FAILED"
        task.error = error
        return task
