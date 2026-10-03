"""Runtime adapter contract for the connected GitHub MCP surface.

The repository code cannot directly own the ChatGPT MCP connection. The Brain
runtime calls this adapter with an injected callable map. This keeps the
project portable while allowing the ChatGPT runtime to dispatch any registered
GitHub tool by exact name.
"""
from __future__ import annotations
from typing import Any, Callable, Mapping
from .github_capability_registry import GITHUB_TOOL_COUNT, has_tool
from .github_executor import GitHubExecutor

class GitHubRuntimeAdapter:
    def __init__(self, tool_map: Mapping[str, Callable[..., Any]],
                 executor: GitHubExecutor | None = None):
        self.tool_map = dict(tool_map)
        self.executor = executor or GitHubExecutor()

    def available_tools(self) -> list[str]:
        return sorted(name for name in self.tool_map if has_tool(name))

    def call(self, tool: str, *, approved: bool = False, **kwargs: Any) -> Any:
        self.executor.plan(tool, approved=approved)
        if tool not in self.tool_map:
            raise RuntimeError(f"GITHUB_RUNTIME_TOOL_NOT_BOUND:{tool}")
        return self.tool_map[tool](**kwargs)

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
        }
