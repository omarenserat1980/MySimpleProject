from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ResourceRequirement:
    cpu_cores:int=1
    ram_bytes:int=0
    storage_bytes:int=0
    network:bool=False
    gpu:bool=False

@dataclass(frozen=True)
class ResourceReservation:
    task_id:str
    blade_id:str
    requirement:ResourceRequirement

@dataclass
class ResourceManager:
    """Resource accounting with explicit, immutable reservations."""
    reservations:dict[str,ResourceReservation]=field(default_factory=dict)

    @staticmethod
    def _ram_used(computer)->int:
        return sum(1 for value in computer.ram._data if value!=0)

    @staticmethod
    def _storage_used(computer)->int:
        return sum(len(value) for value in computer.storage.files.values())

    def snapshot(self,blade)->dict:
        c=blade.computer; ram_used=self._ram_used(c); storage_used=self._storage_used(c)
        cpu_cores=1
        cpu_load=100 if not c.powered else min(100,int(c.cpu.cycles/max(1,c.cpu.cycles+100)*100))
        return {"blade_id":blade.blade_id,"state":blade.state,"capabilities":sorted(blade.capabilities),
          "cpu":{"architecture":"brain-virtual","cores":cpu_cores,"load_percent":cpu_load,"cycles":c.cpu.cycles},
          "ram":{"total_bytes":c.ram.size,"used_bytes":ram_used,"free_bytes":c.ram.size-ram_used},
          "storage":{"total_bytes":c.storage.capacity,"used_bytes":storage_used,"free_bytes":c.storage.capacity-storage_used},
          "network":{"available":"network" in blade.capabilities,"rx_packets":len(c.nic.rx),"tx_packets":len(c.nic.tx)},
          "gpu":{"available":"gpu" in blade.capabilities,"width":c.gpu.width,"height":c.gpu.height}}

    def reserved_for_blade(self,blade_id):
        total=ResourceRequirement(cpu_cores=0)
        for reservation in self.reservations.values():
            if reservation.blade_id==blade_id:
                r=reservation.requirement
                total=ResourceRequirement(total.cpu_cores+r.cpu_cores,total.ram_bytes+r.ram_bytes,total.storage_bytes+r.storage_bytes,total.network or r.network,total.gpu or r.gpu)
        return total

    def can_allocate(self,blade,requirement):
        r=self.snapshot(blade); reserved=self.reserved_for_blade(blade.blade_id)
        return (blade.state=="ONLINE" and requirement.cpu_cores+reserved.cpu_cores<=r["cpu"]["cores"]
          and requirement.ram_bytes+reserved.ram_bytes<=r["ram"]["free_bytes"]
          and requirement.storage_bytes+reserved.storage_bytes<=r["storage"]["free_bytes"]
          and (not requirement.network or r["network"]["available"])
          and (not requirement.gpu or r["gpu"]["available"]))

    def reserve(self,blade,task_id,requirement):
        if task_id in self.reservations: return {"ok":True,"status":"ALREADY_RESERVED","task_id":task_id}
        if not self.can_allocate(blade,requirement): return {"ok":False,"status":"INSUFFICIENT_RESOURCES","task_id":task_id}
        self.reservations[task_id]=ResourceReservation(task_id,blade.blade_id,requirement)
        return {"ok":True,"status":"RESERVED","task_id":task_id,"blade_id":blade.blade_id}

    def release(self,task_id):
        existed=self.reservations.pop(task_id,None) is not None
        return {"ok":existed,"status":"RELEASED" if existed else "NOT_RESERVED","task_id":task_id}

    def rebuild(self,reservations):
        self.reservations={r.task_id:r for r in reservations}

    def cluster(self,chassis):
        resources=[self.snapshot(blade) for blade in chassis.blades.values()]
        return {"blade_count":len(resources),"online":sum(x["state"]=="ONLINE" for x in resources),
          "resources":resources,"reservations":len(self.reservations)}
