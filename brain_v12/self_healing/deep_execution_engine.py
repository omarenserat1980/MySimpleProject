"""Bounded deep execution controller for Electronic Brain.

Depth is measured by verified operations between external gates, not by prompt size.
The controller batches safe work, checkpoints state, deduplicates completed work,
and escalates only when evidence shows the current depth is insufficient.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Any


DEPTH_BUDGETS = {
    0: 1,
    1: 5,
    2: 20,
    3: 50,
    4: 100,
    5: 250,
    6: 500,
    7: 1000,
}


@dataclass
class Operation:
    op_id: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        raw = json.dumps(
            {"action": self.action, "payload": self.payload},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class DeepExecutionPolicy:
    depth: int = 3
    max_operations: int | None = None
    max_failures: int = 3
    checkpoint_every: int = 10
    retry_limit: int = 1

    @property
    def budget(self) -> int:
        base = DEPTH_BUDGETS.get(max(0, min(self.depth, 7)), 1000)
        return max(1, min(base, self.max_operations or base))


class DeepExecutionEngine:
    """Execute a bounded operation graph without requiring an external gate per step."""

    schema = "brain-deep-execution/v1"

    def __init__(
        self,
        state_dir: str | Path = ".brain/state",
        policy: DeepExecutionPolicy | None = None,
        executor: Callable[[Operation], dict[str, Any]] | None = None,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.policy = policy or DeepExecutionPolicy()
        self.executor = executor or self._default_executor
        self.checkpoint_path = self.state_dir / "deep_execution_checkpoint.json"

    def _default_executor(self, operation: Operation) -> dict[str, Any]:
        return {"status": "PLANNED", "operation": operation.action}

    def load_checkpoint(self) -> dict[str, Any]:
        if not self.checkpoint_path.exists():
            return {"schema": self.schema, "completed": {}, "failures": {}, "history": []}
        try:
            return json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema": self.schema, "completed": {}, "failures": {}, "history": []}

    def save_checkpoint(self, state: dict[str, Any]) -> None:
        tmp = self.checkpoint_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.checkpoint_path)

    def run(self, operations: Iterable[Operation]) -> dict[str, Any]:
        state = self.load_checkpoint()
        state.update({
            "schema": self.schema,
            "depth": self.policy.depth,
            "budget": self.policy.budget,
            "started_at": state.get("started_at", time.time()),
        })

        executed = 0
        skipped = 0
        failed = 0
        results: list[dict[str, Any]] = []

        for operation in operations:
            if executed >= self.policy.budget:
                break

            fp = operation.fingerprint
            if fp in state["completed"]:
                skipped += 1
                continue

            attempts = 0
            result: dict[str, Any] | None = None
            while attempts <= self.policy.retry_limit:
                attempts += 1
                try:
                    result = self.executor(operation)
                    if result.get("status") in {"PASS", "VERIFIED", "COMPLETED", "PLANNED"}:
                        break
                    if attempts > self.policy.retry_limit:
                        failed += 1
                except Exception as exc:  # bounded recovery surface
                    result = {"status": "FAILED", "error": str(exc)}
                    if attempts > self.policy.retry_limit:
                        failed += 1

            result = result or {"status": "FAILED", "error": "no_result"}
            record = {
                "op_id": operation.op_id,
                "fingerprint": fp,
                "action": operation.action,
                "attempts": attempts,
                "result": result,
            }
            results.append(record)
            state["history"].append(record)
            if result.get("status") in {"PASS", "VERIFIED", "COMPLETED", "PLANNED"}:
                state["completed"][fp] = record
            else:
                state["failures"][fp] = record

            executed += 1
            if executed % max(1, self.policy.checkpoint_every) == 0:
                self.save_checkpoint(state)

            if failed >= self.policy.max_failures:
                state["stop_reason"] = "FAILURE_BUDGET_EXCEEDED"
                break

        state["last_run"] = {
            "executed": executed,
            "skipped": skipped,
            "failed": failed,
            "remaining_budget": max(0, self.policy.budget - executed),
        }
        state["status"] = "FAILED" if failed else (
            "COMPLETE" if executed < self.policy.budget else "BUDGET_EXHAUSTED"
        )
        self.save_checkpoint(state)
        return state


def depth_for(operation_count: int) -> int:
    """Return the smallest named depth capable of the requested operation budget."""
    for depth, budget in sorted(DEPTH_BUDGETS.items()):
        if operation_count <= budget:
            return depth
    return 7
