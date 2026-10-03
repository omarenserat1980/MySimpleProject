"""Unified planner for natural GitHub intents.

Keeps intent routing, capability authorization, and verification metadata in
one deterministic object. Actual connected-tool invocation remains delegated
to the runtime.
"""
from __future__ import annotations
from dataclasses import dataclass
from .github_agent_router import GitHubAgentRouter, GitHubRoute
from .github_executor import GitHubExecutor, ExecutionPlan

@dataclass(frozen=True)
class UnifiedGitHubPlan:
    intent: str
    route: GitHubRoute
    execution: ExecutionPlan

class GitHubPlanner:
    def __init__(self, router: GitHubAgentRouter | None = None,
                 executor: GitHubExecutor | None = None):
        self.router = router or GitHubAgentRouter()
        self.executor = executor or GitHubExecutor()

    def plan(self, intent: str, approved: bool = False) -> UnifiedGitHubPlan:
        route = self.router.plan(intent)
        execution = self.executor.plan(route.action, approved=approved)
        return UnifiedGitHubPlan(intent=intent, route=route, execution=execution)

    def describe(self, intent: str) -> dict:
        route = self.router.plan(intent)
        execution = self.executor.plan(route.action, approved=False) if not route.requires_approval else None
        return {
            "ok": True,
            "intent": intent,
            "domain": route.domain,
            "capability": route.capability,
            "tool": route.action,
            "requires_approval": route.requires_approval,
            "execution_ready": execution is not None,
        }
