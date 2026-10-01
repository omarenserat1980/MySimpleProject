from .kernel import BrainKernel

class BrainSupervisor:
    def __init__(self,kernel=None,max_retries=2):
        self.kernel=kernel or BrainKernel()
        self.max_retries=max_retries

    def run(self,task_id,program):
        if task_id not in self.kernel.tasks:
            self.kernel.create_task(task_id)
        task=self.kernel.tasks[task_id]
        while task.attempts <= self.max_retries:
            try:
                result=self.kernel.execute(task_id,program)
                if task.state=="SUCCESS":
                    return {"status":"VERIFIED_COMPLETED","task":task_id,"attempts":task.attempts,"result":result}
            except Exception:
                if task.attempts>self.max_retries: raise
            if task.attempts<=self.max_retries:
                task.state="RETRYING"
                self.kernel._audit("TASK_RETRYING",task_id,attempt=task.attempts)
        return {"status":"FAILED","task":task_id,"attempts":task.attempts,"error":task.error}
