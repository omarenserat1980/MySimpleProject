"""Bounded executor for predicted future-evolution plans; never fakes verification."""
from __future__ import annotations
import subprocess,sys
from typing import Any

# Keep this list bounded and deterministic. Do not include this executor's
# own test module, otherwise python_self_test would recursively invoke itself.
SELF_TESTS=(
    "brain_v12.brain.test_security_guard",
    "brain_v12.brain.test_company_operating_system",
    "brain_v12.brain.test_competitive_evolution",
)

def _self_test_command():
    return [sys.executable,"-m","unittest",*SELF_TESTS,"-v"]

ALLOWLIST={"python_self_test":_self_test_command}

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
    evidence={"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,
              "executor":executor,"tests":SELF_TESTS}
    combined=p.stdout+"\n"+p.stderr
    verified=p.returncode==0 and "Ran " in combined and "OK" in combined
    if verified:
        return {"status":"VERIFIED_COMPLETED","verified":True,"evidence":evidence}
    return {"status":"FAILED","verified":False,"evidence":evidence}
