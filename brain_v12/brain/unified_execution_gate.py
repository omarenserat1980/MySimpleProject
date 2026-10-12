"""Unified authorization gate: path -> capability -> live executor."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutionDecision:
    ok: bool
    status: str
    path_id: str | None = None
    executor_id: str | None = None
    capability: str | None = None
    reason: str = ""

class UnifiedExecutionGate:
    TASK_CAPABILITIES = {
        "internet_download": "internet_download",
        "open_url": "open_url",
        "open_app": "open_app",
        "create_app_project": "create_app_project",
    }

    def __init__(self, paths, capabilities):
        self.paths = paths
        self.capabilities = capabilities

    def choose(self, task: str) -> ExecutionDecision:
        capability = self.TASK_CAPABILITIES.get(task)
        path = self.paths.best("connectivity")
        if path is None:
            return ExecutionDecision(False, "NO_EXECUTION_PATH", capability=capability, reason="no connectivity path")
        if capability is None:
            return ExecutionDecision(True, "AUTHORIZED", path.path_id, reason="non-Android task")
        candidates = self.capabilities.select({capability})
        if not candidates:
            return ExecutionDecision(False, "CAPABILITY_WORKER_OFFLINE", path.path_id, capability=capability, reason="no online authorized executor")
        return ExecutionDecision(True, "AUTHORIZED", path.path_id, candidates[0].executor_id, capability, "path + capability + live worker")
