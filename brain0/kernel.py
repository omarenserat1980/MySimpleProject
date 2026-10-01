from dataclasses import dataclass, field
from .core import BrainVM

STATES=("PENDING","RUNNING","SUCCESS","FAILED","CANCELLED","RETRYING")

@dataclass
class BrainTask:
    task_id:str
    state:str="PENDING"
    attempts:int=0
    evidence:list[dict]=field(default_factory=list)
    error:str|None=None

class BrainKernel:
    def __init__(self):
        self.vm=BrainVM()
        self.tasks={}
        self.memory={}
        self.audit=[]

    def create_task(self,task_id):
        if task_id in self.tasks: raise ValueError("TASK_EXISTS")
        task=BrainTask(task_id)
        self.tasks[task_id]=task
        self._audit("TASK_CREATED",task_id)
        return task

    def _audit(self,event,task_id,**data):
        self.audit.append({"event":event,"task_id":task_id,**data})

    def execute(self,task_id,program,max_steps=1000):
        task=self.tasks[task_id]
        task.state="RUNNING"; task.attempts+=1; task.error=None
        self._audit("TASK_RUNNING",task_id,attempt=task.attempts)
        try:
            self.vm.load(program)
            result=self.vm.run(max_steps)
            task.evidence=list(result["evidence"])
            task.state="SUCCESS" if result["status"]=="VERIFIED_COMPLETED" else "FAILED"
            self._audit("TASK_VERIFIED" if task.state=="SUCCESS" else "TASK_FAILED_VERIFICATION",task_id,steps=result["steps"])
            return result
        except Exception as exc:
            task.state="FAILED"; task.error=str(exc)
            self._audit("TASK_ERROR",task_id,error=str(exc))
            raise
