from __future__ import annotations
from dataclasses import dataclass, field
from uuid import uuid4
from .virtual_hardware.computer import VirtualComputer
from .brain.resource_manager import ResourceManager, ResourceRequirement

@dataclass
class BladeServer:
    blade_id: str
    computer: VirtualComputer
    state: str = "OFFLINE"
    capabilities: set[str] = field(default_factory=lambda: {"cpu","ram","storage","network","gpu"})

    def power_on(self):
        self.computer.power_on(); self.state="ONLINE"; return self.status()

    def power_off(self):
        self.computer.power_off(); self.state="OFFLINE"; return self.status()

    def execute(self,program,max_cycles=10000):
        if self.state!="ONLINE": raise RuntimeError("BLADE_OFFLINE")
        result=self.computer.execute(program,max_cycles)
        return {"ok":True,"blade_id":self.blade_id,"result":result}

    def status(self):
        return {"blade_id":self.blade_id,"state":self.state,"capabilities":sorted(self.capabilities),"computer":self.computer.status()}

class BladeChassis:
    def __init__(self,name="BRAIN-CHASSIS-01"):
        self.name=name; self.blades={}

    def create_blade(self,capabilities=None,ram_size=65536):
        blade_id=f"blade-{uuid4().hex[:12]}"
        computer=VirtualComputer(blade_id,ram_size=ram_size)
        blade=BladeServer(blade_id,computer,capabilities=set(capabilities or {"cpu","ram","storage","network","gpu"}))
        self.blades[blade_id]=blade
        return blade

    def remove_blade(self,blade_id):
        blade=self.blades.pop(blade_id,None)
        if blade and blade.state=="ONLINE": blade.power_off()
        return bool(blade)

    def status(self):
        return {"name":self.name,"blade_count":len(self.blades),"online":sum(b.state=="ONLINE" for b in self.blades.values()),
                "blades":[b.status() for b in self.blades.values()]}

    def select(self,required_capabilities:set[str], requirement:ResourceRequirement|None=None, resource_manager=None):
        candidates=[b for b in self.blades.values()
                    if b.state=="ONLINE" and required_capabilities.issubset(b.capabilities)
                    and (resource_manager is None or requirement is None or resource_manager.can_allocate(b,requirement))]
        if not candidates:
            return None
        if resource_manager:
            return max(candidates, key=lambda b:(resource_manager.snapshot(b)["ram"]["free_bytes"],
                                                resource_manager.snapshot(b)["storage"]["free_bytes"]))
        return candidates[0]

class BladeScheduler:
    def __init__(self,chassis:BladeChassis,resource_manager=None):
        self.chassis=chassis
        self.resources=resource_manager or ResourceManager()
    def dispatch(self,program,required_capabilities=None,max_cycles=10000,task_id=None,resource_requirement=None):
        required=set(required_capabilities or {"cpu"})
        requirement=resource_requirement or ResourceRequirement()
        task_id=task_id or f"task-{uuid4().hex[:12]}"
        blade=self.chassis.select(required,requirement,self.resources)
        if blade is None:
            return {"ok":False,"status":"NO_CAPABLE_RESOURCE","required":sorted(required),
                    "requirement":requirement.__dict__,"task_id":task_id}
        reservation=self.resources.reserve(blade,task_id,requirement)
        if not reservation["ok"]:
            return {"ok":False,"status":"RESOURCE_RESERVATION_FAILED","reservation":reservation}
        try:
            result=blade.execute(program,max_cycles)
            return {"ok":True,"status":"COMPLETED","blade_id":blade.blade_id,
                    "task_id":task_id,"reservation":reservation,"result":result}
        finally:
            self.resources.release(task_id)
