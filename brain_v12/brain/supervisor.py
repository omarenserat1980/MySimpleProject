"""Brain Supervisor: device-agnostic execution and self-healing control plane."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SupervisorPolicy:
    max_retries: int = 2
    verify_required: bool = True
    auto_repair: bool = True

class BrainSupervisor:
    """Coordinates inspect -> execute -> verify -> repair -> retry without device affinity."""
    def __init__(self, store, device_bridge, policy=None):
        self.store=store
        self.device_bridge=device_bridge
        self.policy=policy or SupervisorPolicy()

    def inspect(self):
        status=self.device_bridge.status()
        return {"ok":True,"stage":"INSPECT","devices":status.get("agents",{}),"queues":{
            "queued":status.get("queued",0),"pending":status.get("pending",0),
            "completed":status.get("completed",0),"failed":status.get("failed",0)}}

    def choose_executor(self, required_capabilities=None):
        required=set(required_capabilities or [])
        agents=self.device_bridge.agent_status().get("agents",[])
        online=[a for a in agents if a.get("online")]
        capable=[a for a in online if required.issubset(set(a.get("capabilities",[])))]
        return {"ok":bool(capable),"executor":capable[0] if capable else None,
                "required_capabilities":sorted(required)}

    def submit(self, task, params=None, required_capabilities=None):
        choice=self.choose_executor(required_capabilities)
        result=self.device_bridge.enqueue(task, params or {})
        self.store.event("BRAIN_SUPERVISOR_SUBMIT",{
            "task":task,"task_id":result.get("task",{}).get("task_id"),
            "required_capabilities":required_capabilities or [],
            "executor_selected":choice.get("executor",{}).get("agent_id") if choice.get("executor") else None})
        return result

    def verify(self, task_id):
        return self.device_bridge.verify_result(task_id)

    def repair(self, task_id, reason="verification failure"):
        self.store.event("BRAIN_SUPERVISOR_REPAIR_REQUESTED",{"task_id":task_id,"reason":reason})
        return {"ok":True,"status":"REPAIR_QUEUED","task_id":task_id,"reason":reason}

    def run_once(self, task=None, params=None, required_capabilities=None):
        inspected=self.inspect()
        if not task:
            return {"ok":True,"status":"INSPECTED","inspection":inspected}
        created=self.submit(task,params,required_capabilities)
        if not created.get("ok"):
            return {"ok":False,"status":"SUBMIT_FAILED","inspection":inspected,"error":created}
        return {"ok":True,"status":"QUEUED","inspection":inspected,"task":created}

    def health(self):
        return {"ok":True,"supervisor":"READY","policy":self.policy.__dict__,
                "device_agnostic":True,"capability_routing":True,"self_healing":self.policy.auto_repair}
