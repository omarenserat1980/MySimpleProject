from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable, Any


@dataclass(frozen=True)
class ChangePlan:
    plan_id: str
    target: str
    baseline_sha: str
    proposed_sha: str
    description: str


@dataclass(frozen=True)
class AgentResult:
    status: str
    baseline_sha: str
    proposed_sha: str
    tests_passed: bool
    verified: bool
    committed: bool
    commit_sha: str | None = None
    error: str | None = None


class GitHubCodeAgent:
    """Guarded code-change pipeline. It can prepare/verify/commit, never merge."""

    def __init__(
        self,
        *,
        read: Callable[[str], str],
        test: Callable[[], bool],
        commit: Callable[[str, str], str],
    ) -> None:
        self.read = read
        self.test = test
        self.commit = commit

    @staticmethod
    def digest(content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()

    def prepare(self, *, target: str, proposed_content: str, description: str) -> ChangePlan:
        baseline = self.read(target)
        baseline_sha = self.digest(baseline)
        proposed_sha = self.digest(proposed_content)
        if baseline_sha == proposed_sha:
            raise ValueError("proposed change is identical to baseline")
        return ChangePlan(
            plan_id=f"change:{baseline_sha[:12]}:{proposed_sha[:12]}",
            target=target,
            baseline_sha=baseline_sha,
            proposed_sha=proposed_sha,
            description=description,
        )

    def execute(
        self,
        plan: ChangePlan,
        *,
        apply: Callable[[ChangePlan], Any],
        verify: Callable[[ChangePlan], bool],
    ) -> AgentResult:
        try:
            apply(plan)
            tests_passed = bool(self.test())
            if not tests_passed:
                return AgentResult("FAILED", plan.baseline_sha, plan.proposed_sha, False, False, False, error="tests failed")
            verified = bool(verify(plan))
            if not verified:
                return AgentResult("FAILED", plan.baseline_sha, plan.proposed_sha, True, False, False, error="independent verification failed")
            commit_sha = self.commit(plan.target, plan.description)
            return AgentResult("COMMITTED", plan.baseline_sha, plan.proposed_sha, True, True, True, commit_sha=commit_sha)
        except Exception as exc:
            return AgentResult("FAILED", plan.baseline_sha, plan.proposed_sha, False, False, False, error=str(exc))


__all__ = ["GitHubCodeAgent", "ChangePlan", "AgentResult"]
