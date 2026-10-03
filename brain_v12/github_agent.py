"""Unified Brain-facing GitHub Agent facade."""
from __future__ import annotations
from typing import Any, Callable, Mapping
from .github_planner import GitHubPlanner
from .github_task_engine import GitHubTask, GitHubTaskEngine
from .github_runtime_adapter import GitHubRuntimeAdapter

class BrainGitHubAgent:
    def __init__(self, tool_map: Mapping[str, Callable[..., Any]]):
        self.planner = GitHubPlanner()
        self.tasks = GitHubTaskEngine(self.planner)
        self.runtime = GitHubRuntimeAdapter(tool_map)

    def inspect(self, intent: str) -> dict[str, Any]:
        return self.planner.describe(intent)

    def execute(self, intent: str, *, approved: bool = False, **kwargs: Any) -> dict[str, Any]:
        plan = self.planner.plan(intent, approved=approved)
        task = self.tasks.start(GitHubTask(intent))
        try:
            result = self.runtime.call(plan.execution.tool, approved=approved, **kwargs)
            self.tasks.record_transport_result(task, plan.execution.tool, result)
            return {
                "state": task.state,
                "tool": plan.execution.tool,
                "attempts": task.attempts,
                "result": result,
                "evidence": task.evidence,
            }
        except Exception as exc:
            self.tasks.fail(task, str(exc))
            raise

    def health(self) -> dict[str, Any]:
        return self.runtime.health()
