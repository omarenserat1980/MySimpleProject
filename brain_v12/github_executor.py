"""Policy-aware executor for Brain's GitHub capability registry.

The executor deliberately exposes planning and authorization decisions separately
from tool invocation. Connected MCP tool calls are made by the Brain runtime;
this class supplies deterministic policy decisions and audit-ready envelopes.
"""
from __future__ import annotations
from dataclasses import dataclass
from .github_capability_registry import has_tool, WRITE_OR_MUTATING_TOOLS

@dataclass(frozen=True)
class ExecutionPlan:
    tool: str
    requires_approval: bool
    reason: str

class GitHubExecutor:
    def plan(self, tool: str, approved: bool = False) -> ExecutionPlan:
        if not has_tool(tool):
            raise ValueError(f"UNKNOWN_GITHUB_TOOL:{tool}")
        requires = tool in WRITE_OR_MUTATING_TOOLS
        if requires and not approved:
            raise PermissionError(f"GITHUB_APPROVAL_REQUIRED:{tool}")
        return ExecutionPlan(
            tool=tool,
            requires_approval=requires,
            reason="approved_mutation" if requires else "read_only",
        )

    def verify_envelope(self, tool: str, result) -> dict:
        """Return transport evidence; callers must add domain-specific verification."""
        return {
            "verified": result is not None,
            "tool": tool,
            "verification_level": "transport",
            "note": "Transport success is not business/engineering verification.",
        }
