#!/usr/bin/env python3
"""Evidence-driven repair dispatcher with candidate verification and rollback."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PATCH_FILE=ROOT/".brain"/"state"/"last_applied_patch.diff"

def run(cmd:list[str], env=None)->subprocess.CompletedProcess[str]:
    return subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,env=env)

def verify(actions:list[str])->tuple[bool,list[dict]]:
    allowed={
      "compile":[sys.executable,"-m","compileall","-q","brain_v12"],
      "self-test":[sys.executable,"-m","brain_v12.self_healing.self_test"],
      "tests":[sys.executable,"-m","pytest","-q"],
      "gate":[sys.executable,"-m","brain_v12.self_healing.verification_gate"],
    }
    out=[]
    for name in actions:
      if name not in allowed:
        return False,[{"action":name,"exit_code":2,"error":"not_allowed"}]
      p=run(allowed[name])
      out.append({"action":name,"exit_code":p.returncode,"stdout":p.stdout[-6000:],"stderr":p.stderr[-6000:]})
      if p.returncode!=0: return False,out
    return True,out

def rollback()->bool:
    if not PATCH_FILE.is_file(): return True
    p=run(["git","apply","-R","--whitespace=error-all",str(PATCH_FILE)])
    if p.returncode: return False
    PATCH_FILE.unlink(missing_ok=True); return True

def main()->int:
    actions=[x.strip() for x in os.getenv("BRAIN_REPAIR_ACTIONS","compile,self-test,tests,gate").split(",") if x.strip()]
    candidates=max(1,min(3,int(os.getenv("BRAIN_REPAIR_CANDIDATES","3"))))
    generator=os.getenv("BRAIN_CODE_GENERATOR_COMMAND"); failure=os.getenv("BRAIN_FAILURE_FILE")
    if generator and failure:
      env=os.environ.copy(); env["BRAIN_FAILURE_FILE"]=failure
      for candidate in range(1,candidates+1):
        if PATCH_FILE.is_file() and not rollback(): return 3
        env["BRAIN_REPAIR_CANDIDATE"]=str(candidate)
        agent=subprocess.run([sys.executable,"-m","brain_v12.self_healing.code_repair_agent"],cwd=ROOT,env=env,text=True,capture_output=True,timeout=int(os.getenv("BRAIN_GENERATOR_TIMEOUT","600")))
        print("BRAIN_REPAIR_CANDIDATE_RESULT=" + str(candidate) + " exit=" + str(agent.returncode), flush=True)
        print("BRAIN_REPAIR_AGENT_STDOUT=" + agent.stdout[-6000:], flush=True)
        print("BRAIN_REPAIR_AGENT_STDERR=" + agent.stderr[-6000:], flush=True)
        if agent.returncode:
          continue
        ok,results=verify(actions)
        evidence={"candidate":candidate,"verified":ok,"verification":results}
        (ROOT/".brain"/"state"/"last_repair_candidate.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
        print("BRAIN_REPAIR_VERIFICATION=" + json.dumps(evidence, ensure_ascii=False, sort_keys=True), flush=True)
        if ok:
          print("REPAIR_DISPATCH=VERIFIED"); return 0
        if not rollback(): return 3
      return 1
    ok,results=verify(actions)
    print(json.dumps(results,ensure_ascii=False))
    return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
