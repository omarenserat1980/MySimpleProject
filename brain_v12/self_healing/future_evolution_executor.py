"""Bounded executor for predicted future-evolution plans; never fakes verification."""
from __future__ import annotations
import subprocess,sys
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ExecutionResult:
    status:str
    verified:bool
    evidence:dict[str,Any]

ALLOWLIST={"python_self_test":lambda: [sys.executable,"-m","unittest"]}

def execute_prediction(plan:dict[str,Any],timeout=180)->dict[str,Any]:
    if plan.get("status")!="PREDICTED":
        return {"status":"PLANNED","verified":False,"reason":"PREDICTION_NOT_READY"}
    if not plan.get("verification"):
        return {"status":"PLANNED","verified":False,"reason":"VERIFICATION_REQUIRED"}
    executor=plan.get("executor")
    if executor not in ALLOWLIST:
        return {"status":"FAILED","verified":False,"reason":"UNKNOWN_EXECUTOR"}
    try:
        p=subprocess.run(ALLOWLIST[executor](),capture_output=True,text=True,timeout=timeout)
    except Exception as exc:
        return {"status":"FAILED","verified":False,"reason":str(exc)[:500]}
    evidence={"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"executor":executor}
    if p.returncode==0:
        return {"status":"VERIFIED_COMPLETED","verified":True,"evidence":evidence}
    return {"status":"FAILED","verified":False,"evidence":evidence}
