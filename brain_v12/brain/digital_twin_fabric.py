"""Brain Digital Twin Fabric.

Virtual devices are first-class test substrates, but their evidence is explicitly
marked SIMULATED and can never satisfy a REAL-world completion gate by itself.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib,json,time
from pathlib import Path
from typing import Any,Callable
from .desktop_commander_emulator import DesktopCommanderEmulator

class Reality(str,Enum):
    SIMULATED="SIMULATED"
    REAL="REAL"

@dataclass(frozen=True)
class TwinPolicy:
    max_twins:int=8
    snapshot_limit:int=20

class RealityGate:
    @staticmethod
    def accept(evidence:dict[str,Any], required:Reality)->dict[str,Any]:
        actual=str(evidence.get("reality","")).upper()
        if actual != required.value:
            return {"ok":False,"status":"REALITY_MISMATCH","required":required.value,"actual":actual}
        if required is Reality.REAL and evidence.get("source") in {"emulator","digital-twin","simulation"}:
            return {"ok":False,"status":"SIMULATION_CANNOT_PROVE_REAL"}
        return {"ok":True,"status":"REALITY_VERIFIED","reality":actual}

class DigitalTwin:
    def __init__(self,node_id:str,root:str|Path):
        self.node_id=node_id
        self.emulator=DesktopCommanderEmulator(root,node_id=node_id)
        self._snapshots:list[dict[str,Any]]=[]

    def snapshot(self,label:str)->dict[str,Any]:
        state={"label":label,"node_id":self.node_id,"files":self.emulator.list_dir("."),
               "processes":self.emulator.process_snapshot(),"created_at":time.time(),"reality":Reality.SIMULATED.value}
        digest=hashlib.sha256(json.dumps(state,sort_keys=True,default=str,separators=(",",":")).encode()).hexdigest()
        record={"snapshot_id":"snap-"+digest[:20],**state,"sha256":digest}
        self._snapshots.append(record)
        return {"ok":True,"snapshot":record}

    def restore_metadata(self,snapshot_id:str)->dict[str,Any]:
        for s in reversed(self._snapshots):
            if s["snapshot_id"]==snapshot_id:
                return {"ok":True,"status":"SNAPSHOT_METADATA_VERIFIED","snapshot":s}
        return {"ok":False,"status":"SNAPSHOT_NOT_FOUND"}

    def inject_failure(self,kind:str)->dict[str,Any]:
        allowed={"heartbeat_timeout","network_down","disk_full","permission_denied","process_crash"}
        if kind not in allowed:return {"ok":False,"status":"FAULT_NOT_SUPPORTED"}
        return {"ok":True,"status":"FAULT_ARMED","fault":kind,"reality":Reality.SIMULATED.value}

class DigitalTwinFabric:
    def __init__(self,root:str|Path,policy: TwinPolicy|None=None):
        self.root=Path(root); self.policy=policy or TwinPolicy()
        self._twins:dict[str,DigitalTwin]={}
        self._faults:dict[str,str]={}

    def create(self,node_id:str)->DigitalTwin:
        if node_id in self._twins:return self._twins[node_id]
        if len(self._twins)>=self.policy.max_twins:raise RuntimeError("DIGITAL_TWIN_LIMIT")
        twin=DigitalTwin(node_id,self.root/node_id)
        self._twins[node_id]=twin
        return twin

    def get(self,node_id:str)->DigitalTwin|None:return self._twins.get(node_id)

    def inventory(self)->dict[str,Any]:
        return {"ok":True,"reality":Reality.SIMULATED.value,"count":len(self._twins),
                "nodes":[t.emulator.info() for t in self._twins.values()]}

    def compare(self,simulated:dict[str,Any],real:dict[str,Any],keys:list[str]|None=None)->dict[str,Any]:
        keys=keys or sorted(set(simulated)|set(real))
        diffs={k:{"simulated":simulated.get(k),"real":real.get(k)} for k in keys if simulated.get(k)!=real.get(k)}
        return {"ok":not diffs,"status":"MATCH" if not diffs else "DIVERGED","differences":diffs}

    def reality_gate(self,evidence:dict[str,Any],required:str="REAL")->dict[str,Any]:
        return RealityGate.accept(evidence,Reality(str(required).upper()))

__all__=["Reality","TwinPolicy","RealityGate","DigitalTwin","DigitalTwinFabric"]
