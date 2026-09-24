#!/usr/bin/env python3
"""V12 Termux Agent: outbound-only authenticated polling bridge."""
import json, os, platform, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

DEFAULT_BASE="https://electronic-brain-v12-gwwg.onrender.com"
AGENT_ID=os.getenv("V12_AGENT_ID","redmi3-01")
BASE_URL=os.getenv("V12_BRAIN_URL",DEFAULT_BASE).rstrip("/")
KEY_FILE=Path(os.getenv("V12_AGENT_KEY_FILE",str(Path.home()/"v12-agent"/"agent.key")))
POLL_SECONDS=max(1.0,float(os.getenv("V12_POLL_SECONDS","2")))
ALLOWED_TASKS={"status","python_version","termux_path","platform"}

def load_key():
    key=KEY_FILE.read_text(encoding="utf-8").strip()
    if not key: raise RuntimeError("V12_AGENT_KEY_FILE is empty")
    return key

def request(method,path,key,payload=None,timeout=25):
    data=None
    headers={"X-V12-Agent-Key":key,"Accept":"application/json"}
    if payload is not None:
        data=json.dumps(payload,ensure_ascii=False).encode()
        headers["Content-Type"]="application/json"
    req=urllib.request.Request(BASE_URL+path,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return json.loads(response.read().decode())

def execute(task,params):
    if task not in ALLOWED_TASKS: return False,{}, "TASK_NOT_ALLOWED"
    if task=="status":
        return True,{"device":platform.system(),"machine":platform.machine(),"python":platform.python_version(),"agent":"V12-Termux-Agent","agent_id":AGENT_ID,"status":"READY"},""
    if task=="python_version": return True,{"python":platform.python_version()},""
    if task=="termux_path": return True,{"path":str(Path.home()/"v12-agent")},""
    if task=="platform": return True,{"system":platform.system(),"release":platform.release(),"machine":platform.machine(),"python":platform.python_version()},""
    return False,{}, "UNHANDLED_TASK"

def main():
    key=load_key()
    print("V12 Termux Agent online:",AGENT_ID)
    print("Brain:",BASE_URL)
    while True:
        try:
            path="/api/device/poll?agent_id="+urllib.parse.quote(AGENT_ID,safe="")
            polled=request("GET",path,key)
            task=polled.get("task")
            if task:
                task_id=task.get("task_id","")
                task_name=task.get("task","")
                params=task.get("params") or {}
                try: ok,result,error=execute(task_name,params)
                except Exception as exc: ok,result,error=False,{},str(exc)[:1000]
                report={"task_id":task_id,"agent_id":AGENT_ID,"ok":ok,"result":result,"error":error}
                print(json.dumps({"task":task_name,"ok":ok,"result":result,"error":error},ensure_ascii=False))
                request("POST","/api/device/report",key,report)
            else:
                time.sleep(POLL_SECONDS)
        except (urllib.error.URLError,TimeoutError,ConnectionError,json.JSONDecodeError) as exc:
            print("connection:",str(exc)[:200]); time.sleep(max(3.0,POLL_SECONDS))
        except KeyboardInterrupt:
            print("V12 Termux Agent stopped."); return
        except Exception as exc:
            print("agent error:",str(exc)[:300]); time.sleep(max(3.0,POLL_SECONDS))

if __name__=="__main__": main()