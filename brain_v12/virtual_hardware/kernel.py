from __future__ import annotations
from dataclasses import dataclass, field
from uuid import uuid4

@dataclass
class VirtualProcess:
    name:str
    pid:str=field(default_factory=lambda:"proc-"+uuid4().hex[:10])
    state:str="READY"
    ticks:int=0

class VirtualKernel:
    """Minimal deterministic kernel with process scheduling and timer ticks."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.processes={}
        self.syscalls=[]
        self.ticks=0
        self.interrupts=[]

    def create_process(self,name):
        p=VirtualProcess(name)
        self.processes[p.pid]=p
        return p

    def terminate(self,pid):
        p=self.processes.get(pid)
        if not p: return False
        p.state="TERMINATED"
        return True

    def tick(self,count:int=1):
        if count<0: raise ValueError("INVALID_TICK_COUNT")
        for _ in range(count):
            self.ticks+=1
            ready=[p for p in self.processes.values() if p.state=="READY"]
            if ready:
                p=ready[(self.ticks-1)%len(ready)]
                p.state="RUNNING"
                p.ticks+=1
                p.state="READY"
            self.interrupts.append({"type":"TIMER","tick":self.ticks})
        return {"ticks":self.ticks,"interrupts":len(self.interrupts)}

    def syscall(self,pid,name,**args):
        if pid not in self.processes: raise KeyError("PROCESS_NOT_FOUND")
        event={"pid":pid,"name":name,"args":args,"tick":self.ticks}
        self.syscalls.append(event)
        return {"ok":True,"event":event}

    def status(self):
        return {"process_count":len(self.processes),
                "processes":[{"pid":p.pid,"name":p.name,"state":p.state,"ticks":p.ticks} for p in self.processes.values()],
                "syscalls":len(self.syscalls),"ticks":self.ticks,"interrupts":len(self.interrupts)}
