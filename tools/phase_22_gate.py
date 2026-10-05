from __future__ import annotations

import os

from platform_foundation.execution_policy import (
    BrainExecutionPolicy,
    ExecutionMode,
    ExecutorDecision,
    ExecutorDescriptor,
)


def phase22_github_optional() -> dict:
    saved = {k: os.environ.get(k) for k in ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS")}
    try:
        for key in saved:
            os.environ.pop(key, None)

        policy = BrainExecutionPolicy(ExecutionMode.BRAIN_ONLY)
        brain = ExecutorDescriptor(
            executor_id="brain-local-01",
            owner="brain",
            persistent=True,
            capabilities=frozenset({"python", "git"}),
        )
        external = ExecutorDescriptor(
            executor_id="github-hosted",
            owner="github",
            persistent=True,
            capabilities=frozenset({"python", "git"}),
        )

        local = policy.select([brain, external], required_capabilities={"python"})
        blocked_without_brain = policy.select(
            [external], required_capabilities={"python"}
        )

        ok = (
            local.decision == ExecutorDecision.ALLOWED
            and local.executor_id == "brain-local-01"
            and blocked_without_brain.decision == ExecutorDecision.BLOCKED
            and all(os.environ.get(k) is None for k in saved)
        )

        return {
            "phase": 22,
            "status": "PASS" if ok else "FAIL",
            "github_dependency": "OPTIONAL",
            "brain_executor_selected": local.executor_id,
            "external_only_decision": blocked_without_brain.decision.value,
            "github_credentials_absent": all(
                os.environ.get(k) is None for k in saved
            ),
        }
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    result = phase22_github_optional()
    print(result)
    raise SystemExit(0 if result["status"] == "PASS" else 1)
