"""Canonical Golden Closed Loop adapter for the Arkan Digital Twin."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .arkan_device_emulator import ArkanDeviceEmulator
from .evidence_store import EvidenceStore
from .golden_closed_loop import GoldenClosedLoop,GoldenTask
from .workload_controller import WorkloadController
from .digital_twin_fabric import RealityGate,Reality

class ArkanTwinGoldenLoop:
    """Compose the existing GoldenClosedLoop; no second orchestrator."""
    def __init__(self,root:str|Path):
        self.root=Path(root)
        self.arkan=ArkanDeviceEmulator(self.root/"arkan")
        self.evidence=EvidenceStore(str(self.root/"evidence.db"))
        self.workload=WorkloadController()
        self._committed:dict[str,Any]={}

    def run(self,script:str,*,task_id="arkan-twin-smoke",max_attempts=2)->dict[str,Any]:
        task=GoldenTask(task_id=task_id,action="powershell-emulator",
                        parameters={"script":script},max_attempts=max_attempts)

        def authorize(t,attempt):
            ready=self.arkan.readiness()
            admission=self.workload.evaluate(queued=0,active=0,key_active=0,
                                             priority="NORMAL",retry_count=attempt-1)
            return {"ok":ready["ok"] and admission["admit"],"verified":ready["ok"],
                    "admit":admission["admit"],"readiness":ready,"admission":admission,
                    "reality":Reality.SIMULATED.value}

        def execute(t,attempt,key):
            result=self.arkan.powershell.run(t.parameters["script"])
            result["execution_key"]=key; result["attempt"]=attempt
            return result

        def observe(t,attempt,result):
            return {"ok":True,"reality":Reality.SIMULATED.value,
                    "execution_ok":bool(result.get("ok")),
                    "output_sha256":self.evidence.digest(result.get("output","")),
                    "attempt":attempt}

        def verify(t,attempt,result,observation):
            if not result.get("ok"): return {"ok":False,"status":"EXECUTION_RESULT_FAILED"}
            if observation.get("reality")!="SIMULATED":
                return {"ok":False,"status":"REALITY_PROVENANCE_INVALID"}
            digest=self.evidence.digest(result.get("output",""))
            if observation["output_sha256"] != digest:
                return {"ok":False,"status":"OUTPUT_INTEGRITY_FAILED"}
            reality=RealityGate.accept({"reality":"SIMULATED","source":"arkan-twin"},Reality.SIMULATED)
            if not reality["ok"]: return {"ok":False,"status":"SIMULATION_REALITY_GATE_FAILED"}
            return {"ok":True,"status":"VERIFIED","reality":"SIMULATED",
                    "output_sha256":digest}

        def commit(t,attempt,verified):
            self._committed[t.task_id]={"attempt":attempt,"status":"COMMITTED",
                                        "reality":"SIMULATED","verification":verified}
            return {"ok":True,"status":"COMMITTED","reality":"SIMULATED"}

        def learn(t,attempt,verified):
            return {"ok":True,"status":"LEARNED",
                    "lesson":"Twin execution verified; real execution remains gated"}

        def recover(t,attempt,error):
            self.arkan.clear_faults()
            return {"ok":True,"status":"RECOVERED","reality":"SIMULATED"}

        return GoldenClosedLoop(
            evidence_store=self.evidence,authorize=authorize,execute=execute,
            observe=observe,verify=verify,commit=commit,learn=learn,recover=recover
        ).run(task)

__all__=["ArkanTwinGoldenLoop"]
