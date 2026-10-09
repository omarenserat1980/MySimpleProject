#!/usr/bin/env python3
"""Brain Device Agent v2: outbound-only, provider-free device bridge."""
from __future__ import annotations
import json, os, platform, sys, time, urllib.parse, urllib.request
from pathlib import Path
from uuid import uuid4

BRAIN_URL=(os.getenv("BRAIN_URL") or os.getenv("V12_BRAIN_URL") or "").rstrip("/")
AGENT_ID=os.getenv("BRAIN_AGENT_ID") or os.getenv("V12_AGENT_ID") or "brain-agent-"+uuid4().hex[:12]
KEY_FILE=Path(os.path.expanduser(os.getenv("BRAIN_AGENT_KEY_FILE") or os.getenv("V12_AGENT_KEY_FILE") or "~/.brain-agent/agent.key"))
POLL_SECONDS=max(2.0,float(os.getenv("BRAIN_AGENT_POLL_SECONDS") or os.getenv("V12_POLL_SECONDS") or "5"))
HEARTBEAT_SECONDS=max(5.0,float(os.getenv("BRAIN_AGENT_HEARTBEAT_SECONDS","10")))
REQUEST_TIMEOUT=max(5.0,float(os.getenv("BRAIN_AGENT_REQUEST_TIMEOUT","30")))
BACKOFF_MAX=max(10.0,float(os.getenv("BRAIN_AGENT_BACKOFF_MAX_SECONDS","60")))
MAX_FAILURES=max(1,int(os.getenv("BRAIN_AGENT_MAX_FAILURES","8")))
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
try:
    from brain_emulator_agent.v12_agent import execute as execute_task
except Exception as exc:
    execute_task=None
    IMPORT_ERROR=f"{type(exc).__name__}:{exc}"
else:
    IMPORT_ERROR=""

def load_key():
    value=os.getenv("BRAIN_AGENT_KEY") or os.getenv("V12_AGENT_KEY")
    if value: return value.strip()
    try: value=KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc: raise RuntimeError(f"agent_key_unavailable:{exc}") from exc
    if not value: raise RuntimeError("agent_key_empty")
    return value

def request(method,path,key,payload=None,params=None):
    if not BRAIN_URL: raise RuntimeError("BRAIN_URL_OR_V12_BRAIN_URL_REQUIRED")
    url=BRAIN_URL+path
    if params: url+="?"+urllib.parse.urlencode(params)
    data=None
    headers={"Accept":"application/json","X-V12-Agent-Key":key,"X-V12-Agent-Id":AGENT_ID,"User-Agent":"Brain-Device-Agent/2.0"}
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
        headers["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=REQUEST_TIMEOUT) as resp:
        raw=resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}

def metadata():
    return {"agent":"BRAIN_DEVICE_AGENT_V2","agent_version":"2.0","agent_id":AGENT_ID,
            "platform":platform.platform(),"system":platform.system(),"machine":platform.machine(),
            "python":platform.python_version(),"cwd":str(Path.cwd()),
            "capabilities":["status","python_version","platform","brain_self_test",
                            "brain_local_painter_draw","brain_machine_cinema_60m",
                            "brain_machine_cinema_120m"],"outbound_only":True}

def run():
    key=load_key()
    if execute_task is None: raise RuntimeError("executor_import_failed:"+IMPORT_ERROR)
    failures=0; backoff=1.0; last_heartbeat=0.0
    print(json.dumps({"status":"STARTING",**metadata()},ensure_ascii=False),flush=True)
    while True:
        try:
            now=time.time()
            if now-last_heartbeat>=HEARTBEAT_SECONDS:
                hb=request("POST","/api/device/heartbeat",key,{"agent_id":AGENT_ID,"metadata":metadata()})
                print(json.dumps({"event":"HEARTBEAT","response":hb},ensure_ascii=False),flush=True)
                last_heartbeat=now
            response=request("GET","/api/device/poll",key,params={"agent_id":AGENT_ID})
            task=response.get("task")
            if task:
                task_id=task.get("task_id"); name=task.get("task"); params=task.get("params") or {}
                print(json.dumps({"event":"CLAIMED","task_id":task_id,"task":name},ensure_ascii=False),flush=True)
                try: ok,result,error=execute_task(name,params)
                except Exception as exc: ok,result,error=False,{},f"{type(exc).__name__}:{exc}"
                report=request("POST","/api/device/report",key,{"task_id":task_id,"agent_id":AGENT_ID,
                                                                  "ok":bool(ok),"result":result,"error":error})
                print(json.dumps({"event":"REPORTED","task_id":task_id,"ok":bool(ok),
                                  "response":report},ensure_ascii=False),flush=True)
            failures=0; backoff=1.0; time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print(json.dumps({"status":"STOPPED"}),flush=True); return 0
        except Exception as exc:
            failures+=1
            print(json.dumps({"event":"CONNECTION_ERROR","failures":failures,
                              "error":f"{type(exc).__name__}:{exc}"},ensure_ascii=False),flush=True)
            time.sleep(min(BACKOFF_MAX,backoff))
            backoff=min(BACKOFF_MAX,backoff*2)
            if failures>=MAX_FAILURES:
                print(json.dumps({"status":"DEGRADED","reason":"connection_failure_budget_exhausted"}),flush=True)
                failures=0; backoff=1.0

if __name__=="__main__":
    raise SystemExit(run())
