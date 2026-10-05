"""Canonical Brain-owned execution gateway.

This is the only runtime authority for production execution. GitHub, CI, and
device adapters are control/evidence integrations; they are never implicit
executors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .execution_policy import BRAIN_INTERNAL, WINDOWS_REAL_BOOT, Executor, choose_executor
from .internal_runner import InternalRunner


@dataclass(frozen=True)
class ExecutionDecision:
    executor: str
    capability: str
    verified: bool
    reason: str


class BrainExecutionGateway:
    """Fail-closed authority for Brain-owned execution."""

    def __init__(self, runner: InternalRunner | None = None) -> None:
        self.runner = runner or InternalRunner()

    def authorize(self, capability: str) -> ExecutionDecision:
        # Production execution is Brain-owned. External executors are not
        # considered candidates for runtime work.
        internal = Executor(
            name=BRAIN_INTERNAL,
            capabilities=frozenset({
                "brain-internal-execution",
                WINDOWS_REAL_BOOT,
                "qemu",
            }),
            priority=0,
            external=False,
        )
        selected = choose_executor((internal,), capability)
        self.runner.require(capability)
        return ExecutionDecision(
            executor=selected.name,
            capability=capability,
            verified=True,
            reason="BRAIN_INTERNAL_AUTHORITY",
        )

    def run(self, argv: list[str], capability: str = "brain-internal-execution",
            cwd: str | None = None, timeout: int | None = None) -> dict[str, Any]:
        decision = self.authorize(capability)
        result = self.runner.run(argv, cwd=cwd, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "executor": decision.executor,
            "authority": "brain-internal",
            "capability": capability,
            "verified_executor": decision.verified,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
