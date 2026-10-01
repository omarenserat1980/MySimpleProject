"""Brain-native development loop.

The Brain decides whether a development task may proceed, records the task,
requires verification, and refuses arbitrary shell execution.
"""
from dataclasses import dataclass, field

from .runtime import BrainRuntime
from .termux_adapter import accept_task


DEVELOPMENT_ACTIONS = {"inspect", "test", "verify", "plan_change"}


@dataclass
class DevelopmentTask:
    task_id: str
    action: str
    target: str
    state: str = "PENDING"
    evidence: list[dict] = field(default_factory=list)


class BrainNativeDeveloper:
    def __init__(self, runtime=None):
        self.runtime = runtime or BrainRuntime()
        self.tasks = {}

    def plan(self, task_id, action, target):
        if action not in DEVELOPMENT_ACTIONS:
            raise ValueError("DEVELOPMENT_ACTION_NOT_ALLOWED")
        if task_id in self.tasks:
            raise ValueError("TASK_EXISTS")
        task = DevelopmentTask(task_id, action, target)
        task.state = "PLANNED"
        task.evidence.append({
            "event": "DEVELOPMENT_PLAN_ACCEPTED",
            "action": action,
            "target": target,
        })
        self.tasks[task_id] = task
        return task

    def verify_capability(self, task_id):
        task = self.tasks[task_id]
        task.state = "VERIFYING"
        for capability in (
            "status", "python_version", "brain_home",
            "platform", "brain0_self_test",
        ):
            accepted = accept_task(capability)
            task.evidence.append({"event": "CAPABILITY_ALLOWED", **accepted})
        task.state = "VERIFIED"
        return task

    def run(self, task_id, program):
        task = self.tasks[task_id]
        if task.state != "VERIFIED":
            raise ValueError("TASK_NOT_VERIFIED")
        result = self.runtime.run(task_id, program)
        task.evidence.append({
            "event": "BRAIN_RUNTIME_RESULT",
            "status": result["status"],
            "attempts": result["attempts"],
            "evidence_chain_valid": result["evidence_chain_valid"],
        })
        task.state = (
            "COMPLETED"
            if result["status"] == "VERIFIED_COMPLETED"
            else "FAILED"
        )
        return result
