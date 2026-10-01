from __future__ import annotations
from dataclasses import dataclass
from time import time

@dataclass
class ExecutionResult:
    ok: bool
    status: str
    executor_id: str
    result: dict
    started_at: float
    finished_at: float

class ExecutorAdapter:
    """Stable interface between Brain scheduling and execution backends."""
    executor_type="generic"

    def __init__(self, executor_id):
        self.executor_id=executor_id

    def capabilities(self):
        raise NotImplementedError

    def execute(self, task):
        raise NotImplementedError

class BladeExecutorAdapter(ExecutorAdapter):
    executor_type="blade"

    def __init__(self, blade):
        super().__init__(blade.blade_id)
        self.blade=blade

    def capabilities(self):
        return set(self.blade.capabilities)

    def execute(self, task):
        started=time()
        try:
            result=self.blade.execute(task.program,task.max_cycles)
            return ExecutionResult(True,"COMPLETED",self.executor_id,result,started,time())
        except Exception as exc:
            return ExecutionResult(False,"FAILED",self.executor_id,{"error":str(exc)},started,time())
