from __future__ import annotations
from dataclasses import dataclass, field
from uuid import uuid4

@dataclass
class VirtualProcess:
    name:str
    pid:str=field(default_factory=lambda:"proc-"+uuid4().hex[:10])
    state:str="READY"

class VirtualKernel:
    """Minimal process and syscall boundary for the Brain virtual computer."""
    def __init__(self):
        self.processes={}
        self.syscalls=[]
    def create_process(self,name):
        p=VirtualProcess(name)
        self.processes[p.pid]=p
        return p
    def terminate(self,pid):
        p=self.processes.get(pid)
        if not p: return False
        p.state="TERMINATED"
        return True
    def syscall(self,pid,name,**args):
        if pid not in self.processes: raise KeyError("PROCESS_NOT_FOUND")
        event={"pid":pid,"name":name,"args":args}
        self.syscalls.append(event)
        return {"ok":True,"event":event}
    def status(self):
        return {"process_count":len(self.processes),"processes":[{"pid":p.pid,"name":p.name,"state":p.state} for p in self.processes.values()],"syscalls":len(self.syscalls)}
