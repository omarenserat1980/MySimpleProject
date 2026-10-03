"""Runtime adapter contract for Brain's connected GitHub tool surface.

The adapter prefers an injected GitHub tool binding. For Actions workflow
dispatch, it can also use the governed in-process REST control plane when the
ChatGPT MCP connector does not expose dispatch_workflow at runtime.
"""
from __future__ import annotations
from typing import Any, Callable, Mapping
from .github_capability_registry import GITHUB_TOOL_COUNT, has_tool
from .github_executor import GitHubExecutor
from .github_actions_operator import GitHubActionsOperator


class GitHubRuntimeAdapter:
    def __init__(
        self,
        tool_map: Mapping[str, Callable[..., Any]],
        executor: GitHubExecutor | None = None,
        actions_operator: GitHubActionsOperator | None = None,
    ):
        self.tool_map = dict(tool_map)
        self.executor = executor or GitHubExecutor()
        self.actions_operator = actions_operator or GitHubActionsOperator()

    def available_tools(self) -> list[str]:
        registered = {name for name in self.tool_map if has_tool(name)}
        if self.actions_operator.github.configured():
            registered.add("dispatch_workflow")
        return sorted(registered)

    def call(self, tool: str, *, approved: bool = False, **kwargs: Any) -> Any:
        self.executor.plan(tool, approved=approved)
        if tool in self.tool_map:
            return self.tool_map[tool](**kwargs)
        if tool == "dispatch_workflow":
            repo_full_name = kwargs.get("repo_full_name") or kwargs.get("repository_full_name")
            workflow_id = kwargs.get("workflow_id")
            if not repo_full_name or not workflow_id:
                raise ValueError("DISPATCH_REQUIRES:repo_full_name,workflow_id")
            return self.actions_operator.dispatch(
                repo_full_name, workflow_id, ref=kwargs.get("ref", "main"),
                inputs=kwargs.get("inputs"), approved=approved,
            )
        raise RuntimeError(f"GITHUB_RUNTIME_TOOL_NOT_BOUND:{tool}")

    def verify(self, tool: str, result: Any) -> dict[str, Any]:
        return self.executor.verify_envelope(tool, result)

    def health(self) -> dict[str, Any]:
        registered = self.available_tools()
        missing = max(0, GITHUB_TOOL_COUNT - len(registered))
        return {
            "ok": missing == 0,
            "registered_tools": len(registered),
            "missing_from_runtime": missing,
            "registry_size": GITHUB_TOOL_COUNT,
            "dispatch_fallback": "available" if "dispatch_workflow" in registered else "unavailable",
        }
