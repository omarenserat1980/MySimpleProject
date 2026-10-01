from __future__ import annotations
from ..blade_server import BladeChassis,BladeScheduler
from ..virtual_hardware.windows_server import WindowsServerVM
from .resource_manager import ResourceManager,ResourceRequirement
from .virtual_task_queue import VirtualTaskQueue
from .capability_registry import CapabilityRegistry
from .executor_adapter import BladeExecutorAdapter
from .supervisor_executor import SupervisorExecutor
from .brain_supervisor import BrainSupervisor

class BrainVirtualDatacenter:
    """Brain-owned datacenter with durable queue and supervisor-controlled execution."""
    def __init__(self,name="BRAIN-DATACENTER-01"):
        self.name=name; self.chassis=BladeChassis(); self.scheduler=BladeScheduler(self.chassis)
        self.resource_manager=ResourceManager(); self.windows_vms={}
        self.task_queue=VirtualTaskQueue(self.chassis,self.resource_manager)
        self.capabilities=CapabilityRegistry(); self.supervisor=BrainSupervisor()
        self.supervisor_executor=SupervisorExecutor(self.supervisor,self.task_queue)

    def provision(self,count=1,capabilities=None):
        blades=[]
        for _ in range(max(0,count)):
            blade=self.chassis.create_blade(capabilities); blade.power_on(); blades.append(blade.status())
        self._sync_capabilities()
        return {"ok":True,"status":"PROVISIONED","count":len(blades),"blades":blades}

    def _sync_capabilities(self):
        self.capabilities=CapabilityRegistry()
        for blade in self.chassis.blades.values():
            self.capabilities.register(blade.blade_id,blade.capabilities)

    def run(self,program,required_capabilities=None,max_cycles=10000):
        return self.scheduler.dispatch(program,required_capabilities,max_cycles)

    def submit_task(self,program,required_capabilities=None,requirement=None,task_id=None,idempotency_key=None):
        return self.supervisor_executor.submit(program,required_capabilities,requirement,task_id)

    def inspect_task(self,task_id,attempt=1,max_attempts=3):
        return self.supervisor_executor.inspect(task_id,attempt,max_attempts)

    def task_status(self,task_id):
        task=self.task_queue.get(task_id)
        if task is None: return {"ok":False,"status":"TASK_NOT_FOUND","task_id":task_id}
        return {"ok":True,"task":task.__dict__}

    def queue_status(self): return self.task_queue.status()
    def resources(self): return self.resource_manager.cluster(self.chassis)

    def blade_resources(self,blade_id):
        blade=self.chassis.blades.get(blade_id)
        if blade is None: return {"ok":False,"status":"BLADE_NOT_FOUND","blade_id":blade_id}
        return {"ok":True,"resource":self.resource_manager.snapshot(blade)}

    def reserve_resources(self,blade_id,task_id,requirement):
        blade=self.chassis.blades.get(blade_id)
        if blade is None: return {"ok":False,"status":"BLADE_NOT_FOUND","blade_id":blade_id}
        if isinstance(requirement,dict): requirement=ResourceRequirement(**requirement)
        return self.resource_manager.reserve(blade,task_id,requirement)

    def release_resources(self,task_id): return self.resource_manager.release(task_id)

    def provision_windows_server_2025(self,blade_id=None,image_path=None,sha256=None,ram_bytes=4*1024*1024*1024,disk_bytes=64*1024*1024*1024):
        if blade_id is None:
            online=[b for b in self.chassis.blades.values() if b.state=="ONLINE"]
            if not online: return {"ok":False,"status":"NO_ONLINE_BLADE"}
            blade_id=online[0].blade_id
        if blade_id not in self.chassis.blades: return {"ok":False,"status":"BLADE_NOT_FOUND","blade_id":blade_id}
        blade=self.chassis.blades[blade_id]; requirement=ResourceRequirement(ram_bytes=ram_bytes,storage_bytes=disk_bytes)
        if not self.resource_manager.can_allocate(blade,requirement):
            return {"ok":False,"status":"INSUFFICIENT_RESOURCES","blade_id":blade_id}
        vm=WindowsServerVM(f"{blade_id}-windows-2025",ram_bytes,disk_bytes)
        media=vm.attach_windows_server_2025(image_path,sha256); self.windows_vms[vm.name]=vm
        return {"ok":True,"status":"VM_DEFINED","blade_id":blade_id,"vm":vm.name,"media":media}

    def boot_windows_server_2025(self,vm_name):
        vm=self.windows_vms.get(vm_name)
        return vm.boot() if vm else {"ok":False,"status":"VM_NOT_FOUND"}

    def status(self):
        s=self.chassis.status()
        return {"ok":True,"name":self.name,"status":"ONLINE" if s["online"] else "EMPTY","chassis":s,
          "resources":self.resources(),"windows_vms":[vm.status() for vm in self.windows_vms.values()],
          "queue":self.queue_status()}
