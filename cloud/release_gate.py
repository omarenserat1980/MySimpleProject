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
  gates=[self._compile(),self._pytest_feedback(),self._pytest_task_engine(),self._api_routes(),self._cinema_truth(),self._governance()]
  all_required=all(g.passed for g in gates if g.required)
  result={"status":"RELEASE_ALLOWED" if all_required else "RELEASE_BLOCKED","evaluated_at":datetime.now(timezone.utc).isoformat(),"gates":[asdict(g) for g in gates],"evidence_contract":{"all_required_gates_passed":all_required,"release_requires_runtime_evidence":True}}
  self._atomic(result); return result

 def _compile(self):
  p=subprocess.run([sys.executable,"-m","compileall","-q","cloud"],capture_output=True,text=True)
  return Gate("compile",True,p.returncode==0,"process://compileall",p.stderr.strip())

 def _pytest_feedback(self):
  p=subprocess.run([sys.executable,"-m","pytest","-q","cloud/test_customer_feedback.py"],capture_output=True,text=True)
  return Gate("feedback_contract",True,p.returncode==0,"process://pytest/customer_feedback",(p.stdout+p.stderr)[-3000:])

 def _pytest_task_engine(self):
  p=subprocess.run([sys.executable,"-m","pytest","-q","brain_v12/brain/task_engine_test.py"],capture_output=True,text=True)
  return Gate("task_engine_evidence_contract",True,p.returncode==0,"process://pytest/task_engine",(p.stdout+p.stderr)[-3000:])

 def _api_routes(self):
  try:
   from cloud.api_server import app
   seen=set(); dup=[]; paths=set()
   for r in app.routes:
    path=getattr(r,"path",None)
    if not path:
     continue
    paths.add(path)
    methods=getattr(r,"methods",set()) or set()
    for m in methods:
     k=(m,path)
     if k in seen: dup.append(k)
     seen.add(k)
   detail=f"duplicates={dup}; route_count={len(paths)}"
   return Gate("api_routes",True,not dup and "/v1/feedback" in paths,"runtime://fastapi/routes",detail)
  except Exception as e:
   return Gate("api_routes",True,False,"runtime://fastapi/import",repr(e))

 def _cinema_truth(self):
  with tempfile.TemporaryDirectory(prefix="brain-release-cinema-") as td:
   env=os.environ.copy()
   env.update({"BRAIN_MACHINE_FILM_ROOT":str(Path(td)/"machine_films"),"BRAIN_FILM_PARTS":"1","BRAIN_FILM_PART_SECONDS":"5","BRAIN_FILM_START":"1","BRAIN_FILM_END":"1","BRAIN_FILM_SHARD_ONLY":"1"})
   p=subprocess.run([sys.executable,"-m","brain_v12.machine_cinematic_factory"],capture_output=True,text=True,env=env,timeout=180)
   if p.returncode:
    return Gate("cinema_truth",True,False,"process://brain_cinematic_factory",(p.stdout+p.stderr)[-3000:])
   root=Path(td)/"machine_films"; manifest=root/"manifest.json"; clip=root/"parts"/"001"/"part-001.mp4"
   if not manifest.exists() or not clip.exists() or clip.stat().st_size<=1024:
    return Gate("cinema_truth",True,False,"process://brain_cinematic_factory",f"manifest={manifest.exists()},clip={clip.exists()}")
   try:
    d=json.loads(manifest.read_text(encoding="utf-8")); q=self._probe_media(clip)
    passed=d.get("status")=="SHARD_COMPLETED" and q["video"] and q["audio"] and q["duration"]>0 and q["width"]>0 and q["height"]>0
    return Gate("cinema_truth",True,passed,"process://brain_cinematic_factory",f"status={d.get('status')},probe={q}")
   except Exception as e:
    return Gate("cinema_truth",True,False,"process://brain_cinematic_factory",repr(e))

 def _probe_media(self,path:Path):
  p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height","-of","json",str(path)],capture_output=True,text=True,timeout=60)
  if p.returncode: raise RuntimeError(p.stderr.strip() or "ffprobe failed")
  d=json.loads(p.stdout); streams=d.get("streams",[])
  return {"duration":float((d.get("format") or {}).get("duration") or 0),"video":any(x.get("codec_type")=="video" for x in streams),"audio":any(x.get("codec_type")=="audio" for x in streams),"width":next((x.get("width") for x in streams if x.get("codec_type")=="video"),0),"height":next((x.get("height") for x in streams if x.get("codec_type")=="video"),0)}

 def _governance(self):
  req=["COMMERCIAL_GOVERNANCE_SPEC.md","PAYMENT_POLICY.md","PUBLIC_IDENTITY_AND_LIMITED_LIABILITY_POLICY.md"]; missing=[x for x in req if not Path(x).exists()]
  return Gate("governance",True,not missing,"repo://governance",f"missing={missing}")

 def _atomic(self,result):
  p=self.root/"release_gate.json"; fd,tmp=tempfile.mkstemp(dir=self.root,prefix=".tmp-")
  try:
   with os.fdopen(fd,"w",encoding="utf-8") as h:
    json.dump(result,h,ensure_ascii=False,indent=2); h.flush(); os.fsync(h.fileno())
   os.replace(tmp,p)
  finally:
   if os.path.exists(tmp): os.unlink(tmp)
