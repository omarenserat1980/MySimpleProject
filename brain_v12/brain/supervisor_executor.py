from __future__ import annotations
from .failure_policy import FailurePolicy

class SupervisorExecutor:
    """Verification-driven bridge: execute, classify failure, and return bounded repair guidance."""
    def __init__(self, supervisor, queue):
        self.supervisor=supervisor
        self.queue=queue
        self.failures=FailurePolicy()

    def submit(self, program, capabilities=None, requirement=None, task_id=None):
        task=self.queue.submit(program,capabilities,requirement,task_id)
        return {"ok":True,"task_id":task.task_id,"status":task.status}

    def inspect(self, task_id, attempt=1, max_attempts=3):
        task=self.queue.get(task_id)
        if task is None:
            return {"ok":False,"status":"TASK_NOT_FOUND"}
        if task.status=="COMPLETED":
            return {"ok":True,"status":"VERIFIED_PENDING_EXTERNAL_GATE","task_id":task_id,"result":task.result}
        if task.status=="FAILED":
            error=(task.result or {}).get("error","execution_failed")
            decision=self.failures.decide(error,attempt,max_attempts)
            return {"ok":False,"status":"FAILED","task_id":task_id,"failure":decision.__dict__}
        return {"ok":False,"status":task.status,"task_id":task_id}
