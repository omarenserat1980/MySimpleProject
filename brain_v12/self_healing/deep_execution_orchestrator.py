"""Deep execution orchestration layer.

Connects bounded operation depth to Brain Supervisor without creating recursive
self-healing loops. A depth promotion requires evidence; completed operations
are checkpointed and never repeated unless their fingerprint changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from brain_v12.self_healing.deep_execution_engine import (
    DeepExecutionEngine, DeepExecutionPolicy, Operation, depth_for,
)


@dataclass(frozen=True)
class DepthGate:
    current: int
    requested: int
    reason: str
    promoted: bool


class DeepExecutionOrchestrator:
    def __init__(
        self,
        executor: Callable[[Operation], dict[str, Any]],
        state_dir: str = ".brain/state/deep",
    ) -> None:
        self.engine = DeepExecutionEngine(
            state_dir=state_dir,
            executor=executor,
        )

    def choose_depth(self, operations: Iterable[Operation], minimum: int = 0) -> int:
        ops = list(operations)
        requested = depth_for(len(ops))
        return max(minimum, requested)

    def run_until_gate(
        self,
        operations: Iterable[Operation],
        *,
        minimum_depth: int = 0,
        max_depth: int = 7,
        promote_on: tuple[str, ...] = ("CAPABILITY_MISSING", "EVIDENCE_INSUFFICIENT"),
    ) -> dict[str, Any]:
        ops = list(operations)
        target = min(max_depth, max(minimum_depth, self.choose_depth(ops, minimum_depth)))
        policy = DeepExecutionPolicy(depth=target)
        self.engine.policy = policy

        state = self.engine.run(ops)
        last = state.get("last_run", {})
        promotion_reason = None

        # Promotion is evidence-driven, not recursive. The caller may invoke
        # this method again with the returned depth; there is never an unbounded loop.
        for record in reversed(state.get("history", [])):
            result = record.get("result", {})
            reason = result.get("reason")
            if reason in promote_on:
                promotion_reason = reason
                break

        gate = DepthGate(
            current=target,
            requested=min(max_depth, target + 1) if promotion_reason else target,
            reason=promotion_reason or "normal_gate",
            promoted=bool(promotion_reason and target < max_depth),
        )
        state["depth_gate"] = {
            "current": gate.current,
            "requested": gate.requested,
            "reason": gate.reason,
            "promoted": gate.promoted,
        }
        return state
