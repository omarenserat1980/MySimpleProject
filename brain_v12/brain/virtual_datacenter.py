from __future__ import annotations
from ..blade_server import BladeChassis, BladeScheduler

class BrainVirtualDatacenter:
    """Brain-owned virtual datacenter: chassis + blades + capability scheduler."""
    def __init__(self,name="BRAIN-DATACENTER-01"):
        self.name=name
        self.chassis=BladeChassis()
        self.scheduler=BladeScheduler(self.chassis)

    def provision(self,count:int=1,capabilities=None):
        blades=[]
        for _ in range(max(0,count)):
            blade=self.chassis.create_blade(capabilities)
            blade.power_on()
            blades.append(blade.status())
        return {"ok":True,"status":"PROVISIONED","count":len(blades),"blades":blades}

    def run(self,program,required_capabilities=None,max_cycles=10000):
        return self.scheduler.dispatch(program,required_capabilities,max_cycles)

    def status(self):
        s=self.chassis.status()
        return {"ok":True,"name":self.name,"status":"ONLINE" if s["online"] else "EMPTY","chassis":s}
