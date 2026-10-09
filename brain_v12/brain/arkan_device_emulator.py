"""Arkan Device Emulator: deterministic virtual twin of the Brain arkan executor."""
from __future__ import annotations
from dataclasses import dataclass,field
from pathlib import Path
import hashlib,json,time
from typing import Any
from .desktop_commander_emulator import DesktopCommanderEmulator
from .powershell_emulator import PowerShellEmulator
from .digital_twin_fabric import Reality

SCHEMA="brain.arkan-device-emulator.v1"

@dataclass
class ArkanProfile:
    device_id:str="d0f5f0a0-f105-4750-8254-cca35dfe9c29"
    name:str="arkan"
    os:str="Windows 10 Pro"
    build:str="26300"
    model:str="ASUS Vivobook X1504VA"
    logical_cpus:int=8
    ram_gib:float=3.63
    architecture:str="x64"
    wsl_distribution:str="Ubuntu-24.04"
    wsl_version:int=2
    labels:list[str]=field(default_factory=lambda:["self-hosted","windows-real-boot","brain-internal"])

class ArkanDeviceEmulator:
    def __init__(self,root:str|Path,profile:ArkanProfile|None=None):
        self.profile=profile or ArkanProfile()
        self.desktop=DesktopCommanderEmulator(root,node_id=self.profile.name)
        self.powershell=PowerShellEmulator(self.desktop)
        self.resources={"cpu_percent":0.0,"memory_percent":0.0,"free_ram_gib":self.profile.ram_gib,
                        "disk_free_gib":64.0}
        self.network={"online":True,"internet_443":True,"kvm":False}
        self.services={"BrainAgent":"RUNNING","GitHubRunner":"RUNNING","WSL":"RUNNING"}
        self.vms={"Brain-Win2025":"STOPPED","Brain-WindowsServer2025":"STOPPED"}
        self.faults:set[str]=set()

    def info(self)->dict[str,Any]:
        return {"ok":True,"schema":SCHEMA,"reality":Reality.SIMULATED.value,
                "device":self.profile.__dict__,"resources":self.resources.copy(),
                "network":self.network.copy(),"services":self.services.copy(),"vms":self.vms.copy()}

    def heartbeat(self)->dict[str,Any]:
        return {"ok":True,"node_id":self.profile.device_id,"name":self.profile.name,
                "state":"DEGRADED" if self.faults else "ONLINE",
                "reality":Reality.SIMULATED.value,"ts":time.time()}

    def set_resources(self,**values:float)->dict[str,Any]:
        for k,v in values.items():
            if k not in self.resources: return {"ok":False,"status":"RESOURCE_NOT_SUPPORTED"}
            self.resources[k]=max(0.0,float(v))
        return {"ok":True,"resources":self.resources.copy(),"reality":Reality.SIMULATED.value}

    def set_network(self,*,online:bool|None=None,internet_443:bool|None=None,kvm:bool|None=None)->dict[str,Any]:
        for k,v in {"online":online,"internet_443":internet_443,"kvm":kvm}.items():
            if v is not None:self.network[k]=bool(v)
        return {"ok":True,"network":self.network.copy(),"reality":Reality.SIMULATED.value}

    def set_service(self,name:str,state:str)->dict[str,Any]:
        if name not in self.services:return {"ok":False,"status":"SERVICE_NOT_FOUND"}
        if state not in {"RUNNING","STOPPED","FAILED"}:return {"ok":False,"status":"SERVICE_STATE_INVALID"}
        self.services[name]=state
        return {"ok":True,"service":name,"state":state,"reality":Reality.SIMULATED.value}

    def set_vm(self,name:str,state:str)->dict[str,Any]:
        if name not in self.vms:return {"ok":False,"status":"VM_NOT_FOUND"}
        if state not in {"RUNNING","STOPPED","FAILED"}:return {"ok":False,"status":"VM_STATE_INVALID"}
        self.vms[name]=state
        return {"ok":True,"vm":name,"state":state,"reality":Reality.SIMULATED.value}

    def inject_fault(self,kind:str)->dict[str,Any]:
        allowed={"ram_pressure","cpu_pressure","network_down","internet_down","runner_offline",
                 "agent_offline","service_failure","vm_failure","disk_pressure"}
        if kind not in allowed:return {"ok":False,"status":"FAULT_NOT_SUPPORTED"}
        self.faults.add(kind)
        if kind=="network_down":self.network["online"]=False
        if kind=="internet_down":self.network["internet_443"]=False
        if kind=="runner_offline":self.services["GitHubRunner"]="STOPPED"
        if kind=="agent_offline":self.services["BrainAgent"]="STOPPED"
        if kind=="vm_failure":self.vms["Brain-WindowsServer2025"]="FAILED"
        return {"ok":True,"status":"FAULT_INJECTED","fault":kind,"reality":Reality.SIMULATED.value}

    def clear_faults(self)->dict[str,Any]:
        self.faults.clear()
        self.network.update(online=True,internet_443=True)
        self.services.update(BrainAgent="RUNNING",GitHubRunner="RUNNING")
        return {"ok":True,"status":"FAULTS_CLEARED","reality":Reality.SIMULATED.value}

    def readiness(self)->dict[str,Any]:
        checks={
          "device_online":not {"network_down"} & self.faults,
          "agent":self.services["BrainAgent"]=="RUNNING",
          "runner":self.services["GitHubRunner"]=="RUNNING",
          "wsl":self.services["WSL"]=="RUNNING",
          "internet_443":self.network["internet_443"],
          "memory_gate":self.resources["free_ram_gib"]>=2.0,
          "disk_gate":self.resources["disk_free_gib"]>=10.0,
          "kvm":self.network["kvm"],
        }
        return {"ok":all(checks.values()),"status":"READY" if all(checks.values()) else "BLOCKED",
                "checks":checks,"reality":Reality.SIMULATED.value}

    def snapshot(self,label:str)->dict[str,Any]:
        state={"label":label,"info":self.info(),"readiness":self.readiness(),"heartbeat":self.heartbeat()}
        digest=hashlib.sha256(json.dumps(state,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()
        return {"ok":True,"snapshot_id":"arkan-sim-"+digest[:20],"sha256":digest,
                "reality":Reality.SIMULATED.value,"state":state}

__all__=["ArkanProfile","ArkanDeviceEmulator","SCHEMA"]
