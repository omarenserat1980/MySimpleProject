from __future__ import annotations
from dataclasses import dataclass, field
from uuid import uuid4
from .virtual_hardware.computer import VirtualComputer

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

    def select(self,required_capabilities:set[str]):
        candidates=[b for b in self.blades.values() if b.state=="ONLINE" and required_capabilities.issubset(b.capabilities)]
        return candidates[0] if candidates else None

class BladeScheduler:
    def __init__(self,chassis:BladeChassis):
        self.chassis=chassis
    def dispatch(self,program,required_capabilities=None,max_cycles=10000):
        required=set(required_capabilities or {"cpu"})
        blade=self.chassis.select(required)
        if blade is None: return {"ok":False,"status":"NO_CAPABLE_BLADE","required":sorted(required)}
        result=blade.execute(program,max_cycles)
        return {"ok":True,"status":"COMPLETED","blade_id":blade.blade_id,"result":result}
