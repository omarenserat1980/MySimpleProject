"""Integrated BRAIN-0/1 runtime."""
from .kernel import BrainKernel
from .memory import Memory
from .evidence import EvidenceChain
from .supervisor import BrainSupervisor

class BrainRuntime:
    def __init__(self):
        self.memory=Memory()
        self.evidence=EvidenceChain()
        self.kernel=BrainKernel()
        self.supervisor=BrainSupervisor(self.kernel)

    def run(self,task_id,program):
        self.evidence.append("TASK_REQUESTED",task_id=task_id,program_size=len(program))
        result=self.supervisor.run(task_id,program)
        self.evidence.append("TASK_RESULT",task_id=task_id,status=result["status"],attempts=result["attempts"])
        self.memory.put("last_task",task_id)
        self.memory.put("last_status",result["status"])
        result["memory"]=self.memory.snapshot()
        result["evidence_chain_valid"]=self.evidence.verify()
        result["audit"]=self.kernel.audit
        return result
