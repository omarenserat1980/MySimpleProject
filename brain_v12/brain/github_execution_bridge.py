"""Evidence-first bridge between the GitHub Agent and Brain Execution Coordinator.

The GitHub Agent remains responsible for intent routing and mutation approval.
The coordinator owns bounded lifecycle, verification, retry, repair, and
evidence-gated completion.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from ..github_agent import BrainGitHubAgent
from .execution_coordinator import BrainExecutionCoordinator

GitHubVerifier = Callable[[dict[str, Any]], dict[str, Any] | bool]
Repairer = Callable[[dict[str, Any]], dict[str, Any] | None]


class BrainGitHubExecutionBridge:
    """Run GitHub intents through the unified evidence-first coordinator."""

    def __init__(
        self,
        agent: BrainGitHubAgent,
        coordinator: BrainExecutionCoordinator | None = None,
    ) -> None:
        self.agent = agent
        self.coordinator = coordinator or BrainExecutionCoordinator()

    def create(self, intent: str, max_attempts: int = 3) -> dict[str, Any]:
        return self.coordinator.create(f"github:{intent}", max_attempts=max_attempts)

    def execute(
        self,
        control_task_id: str,
        intent: str,
        *,
        approved: bool = False,
        verifier: GitHubVerifier,
        repair: Repairer | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        def executor(_: str) -> dict[str, Any]:
            result = self.agent.execute(intent, approved=approved, **kwargs)
            if not isinstance(result, dict):
                raise TypeError("github agent must return a mapping")
            return result

        return self.coordinator.execute(
            control_task_id,
            executor,
            verifier,
            repair=repair,
        )

    def inspect(self, intent: str) -> dict[str, Any]:
        return self.agent.inspect(intent)

    def snapshot(self) -> dict[str, Any]:
        return self.coordinator.snapshot()
