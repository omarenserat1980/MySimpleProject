#!/usr/bin/env python3
"""Brain Termux Emulator agent with heartbeat, polling and allowlisted execution."""
import json, os, platform, subprocess, sys, time, urllib.parse, urllib.request
from uuid import uuid4

SELF_TESTS = (
    "brain_v12.brain.test_security_guard",
    "brain_v12.brain.test_company_operating_system",
    "brain_v12.brain.test_competitive_evolution",
    "brain_v12.self_healing.test_future_evolution_executor",
)
BRAIN_URL = os.getenv("V12_BRAIN_URL", "http://127.0.0.1:8012").rstrip("/")
AGENT_ID = os.getenv("V12_AGENT_ID") or "agent-" + uuid4().hex[:12]
KEY_FILE = os.path.expanduser(os.getenv("V12_AGENT_KEY_FILE", "~/v12-agent/agent.key"))
POLL_SECONDS = max(2, int(os.getenv("V12_POLL_SECONDS", os.getenv("V12_AGENT_POLL_SECONDS", "5")))

def load_key():
    with open(KEY_FILE, encoding="utf-8") as f: key=f.read().strip()
    if not key: raise RuntimeError("V12_AGENT_KEY_FILE is empty")
    return key

def request_json(method, path, key, payload=None):
    data=None
    headers={"Accept":"application/json","X-V12-Agent-Key":key}
    if payload is not None:
        data=json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"]="application/json"
    req=urllib.request.Request(BRAIN_URL+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def execute(task):
    if task=="status":
        return {"device":platform.system(),"machine":platform.machine(),"python":platform.python_version(),"agent":"V12-BRAIN-EMULATOR","status":"READY"}
    if task=="python_version":
        p=subprocess.run([sys.executable,"--version"],capture_output=True,text=True,timeout=10)
        return {"returncode":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}
    if task=="brain_home":
        p=subprocess.run(["pwd"],capture_output=True,text=True,timeout=10)
        return {"returncode":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}
    if task=="platform":
        return {"system":platform.system(),"release":platform.release(),"version":platform.version(),"machine":platform.machine()}
    if task=="brain_self_test":
        root=os.path.abspath(os.path.join(os.path.dirname(__file__),"..",".."))
        env=dict(os.environ); env["PYTHONPATH"]=root+os.pathsep+env.get("PYTHONPATH","")
        p=subprocess.run([sys.executable,"-m","unittest",*SELF_TESTS,"-v"],cwd=root,env=env,capture_output=True,text=True,timeout=180)
        return {"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"tests":SELF_TESTS}
    raise ValueError("TASK_NOT_ALLOWED")

def main():
    key=load_key()
    print(f"JET_BRAIN_EMULATOR connected to {BRAIN_URL}",flush=True)
    print(f"Agent ID: {AGENT_ID}",flush=True)
    while True:
        try:
            q=urllib.parse.urlencode({"agent_id":AGENT_ID})
            request_json("POST","/api/device/heartbeat",key,{"agent_id":AGENT_ID,"metadata":{"agent":"BRAIN_EMULATOR","python":platform.python_version()}})
            response=request_json("GET","/api/device/poll?"+q,key)
            task=response.get("task")
            if task:
                task_id,name=task["task_id"],task["task"]
                try:
                    result=execute(name); ok=True; error=""
                except Exception as exc:
                    result={}; ok=False; error=str(exc)[:1000]
                out=request_json("POST","/api/device/report",key,{"task_id":task_id,"agent_id":AGENT_ID,"ok":ok,"result":result,"error":error})
                print(json.dumps({"task":task_id,"name":name,"report":out},ensure_ascii=False),flush=True)
            else: print("IDLE",flush=True)
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt: return
        except Exception as exc:
            print(f"connection/error: {exc}",flush=True)
            time.sleep(max(POLL_SECONDS,5))

if __name__=="__main__": main()
