"""Evidence-first Brain release gate."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from pathlib import Path
import json,os,subprocess,sys,tempfile
@dataclass
class Gate:
 name:str; required:bool; passed:bool; evidence:str; detail:str=""
class ReleaseGate:
 def __init__(self,root:Path|None=None):
  self.root=Path(root or os.getenv("BRAIN_STATE_DIR",".brain_state"))/"release_gate"; self.root.mkdir(parents=True,exist_ok=True)
 def run(self):
  gates=[self._compile(),self._pytest_feedback(),self._api_routes(),self._cinema_truth(),self._governance()]
  result={"status":"RELEASE_ALLOWED" if all(g.passed for g in gates if g.required) else "RELEASE_BLOCKED","evaluated_at":datetime.now(timezone.utc).isoformat(),"gates":[asdict(g) for g in gates]}; self._atomic(result); return result
 def _compile(self):
  p=subprocess.run([sys.executable,"-m","compileall","-q","cloud"],capture_output=True,text=True); return Gate("compile",True,p.returncode==0,"process://compileall",p.stderr.strip())
 def _pytest_feedback(self):
  p=subprocess.run([sys.executable,"-m","pytest","-q","cloud/test_customer_feedback.py"],capture_output=True,text=True); return Gate("feedback_contract",True,p.returncode==0,"process://pytest/customer_feedback",(p.stdout+p.stderr)[-3000:])
 def _api_routes(self):
  try:
   from cloud.api_server import app
   seen=set(); dup=[]
   for r in app.routes:
    for m in getattr(r,"methods",set()):
     k=(m,r.path)
     if k in seen: dup.append(k)
     seen.add(k)
   paths={r.path for r in app.routes}; return Gate("api_routes",True,not dup and "/v1/feedback" in paths,"runtime://fastapi/routes",f"duplicates={dup}")
  except Exception as e:return Gate("api_routes",True,False,"runtime://fastapi/import",repr(e))
 def _cinema_truth(self):
  p=Path("docs/film.json")
  if not p.exists():return Gate("cinema_truth",True,False,"file://docs/film.json","missing metadata")
  try:
   d=json.loads(p.read_text(encoding="utf-8")); v=Path("docs")/d.get("video",""); ready=all(d.get("status",{}).get(k)=="ready" for k in ("render","video","audio","verification","web")); artifact=v.is_file() and v.stat().st_size>1024; verified=ready and artifact
   return Gate("cinema_truth",True,verified,str(v),f"ready={ready},artifact={artifact}")
  except Exception as e:return Gate("cinema_truth",True,False,"file://docs/film.json",repr(e))
 def _governance(self):
  req=["COMMERCIAL_GOVERNANCE_SPEC.md","PAYMENT_POLICY.md","PUBLIC_IDENTITY_AND_LIMITED_LIABILITY_POLICY.md"]; missing=[x for x in req if not Path(x).exists()]; return Gate("governance",True,not missing,"repo://governance",f"missing={missing}")
 def _atomic(self,result):
  p=self.root/"release_gate.json"; fd,tmp=tempfile.mkstemp(dir=self.root,prefix=".tmp-")
  try:
   with os.fdopen(fd,"w",encoding="utf-8") as h: json.dump(result,h,ensure_ascii=False,indent=2); h.flush(); os.fsync(h.fileno())
   os.replace(tmp,p)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
