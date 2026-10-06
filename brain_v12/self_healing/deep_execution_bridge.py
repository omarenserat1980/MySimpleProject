"""Bounded bridge between Deep Execution and BrainSupervisor.

The bridge makes deep execution a first-class supervisor phase. It records one
meaningful gate per batch and never starts a second autonomous loop in parallel.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from brain_v12.brain.brain_supervisor import BrainSupervisor
from brain_v12.self_healing.deep_execution_engine import Operation
from brain_v12.self_healing.deep_execution_orchestrator import DeepExecutionOrchestrator


class SupervisorDeepExecutionBridge:
    def __init__(
        self,
        supervisor: BrainSupervisor,
        executor: Callable[[Operation], dict[str, Any]],
        state_dir: str = ".brain/state/deep",
    ) -> None:
        self.supervisor = supervisor
        self.deep = DeepExecutionOrchestrator(executor, state_dir)

    def execute_batch(
        self,
        job: dict[str, Any],
        operations: Iterable[Operation],
        *,
        minimum_depth: int = 0,
        max_depth: int = 7,
    ) -> dict[str, Any]:
        ops = list(operations)
        self.supervisor.transition(
            job,
            "execute",
            status="running",
            details={"mode": "deep", "operation_count": len(ops)},
        )
        result = self.deep.run_until_gate(
            ops,
            minimum_depth=minimum_depth,
            max_depth=max_depth,
        )
        status = "completed" if result.get("failed", 0) == 0 else "failed"
        self.supervisor.transition(
            job,
            "verify",
            status="running",
            details={
                "mode": "deep",
                "depth": result.get("depth"),
                "last_run": result.get("last_run", {}),
                "depth_gate": result.get("depth_gate", {}),
            },
        )
        return {
            "status": status,
            "job_id": job.get("job_id"),
            "depth": result.get("depth"),
            "last_run": result.get("last_run", {}),
            "depth_gate": result.get("depth_gate", {}),
            "checkpoint": str(self.deep.engine.checkpoint_path),
        }
