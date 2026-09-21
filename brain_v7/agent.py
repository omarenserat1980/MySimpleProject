import os, subprocess, time, json, pathlib, platform
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

TOKEN=os.getenv("AGENT_TOKEN","")
SANDBOX=pathlib.Path(os.getenv("AGENT_SANDBOX","./agent_sandbox")).resolve()
SANDBOX.mkdir(parents=True,exist_ok=True)
MAX_OUTPUT=int(os.getenv("AGENT_MAX_OUTPUT","12000"))
ALLOWED_COMMANDS=set(filter(None,os.getenv("AGENT_COMMANDS","python,python3,pip,git,pytest").split(",")))

app=FastAPI(title="Electronic Brain Agent",version="1.0")

class ExecIn(BaseModel):
    command:list[str]
    timeout:int=30
    cwd:str="."

def auth(token):
    if not TOKEN or token!=TOKEN:
        raise HTTPException(401,"AGENT_AUTH_REQUIRED")

def safe_path(p):
    q=(SANDBOX/pathlib.Path(p)).resolve()
    if q!=SANDBOX and SANDBOX not in q.parents:
        raise HTTPException(403,"PATH_OUTSIDE_SANDBOX")
    return q

@app.get("/health")
def health():
    return {"ok":True,"agent":"Electronic Brain Agent","sandbox":str(SANDBOX),"platform":platform.platform()}

@app.post("/execute")
def execute(token:str, body:ExecIn):
    auth(token)
    if not body.command or body.command[0] not in ALLOWED_COMMANDS:
        raise HTTPException(403,"COMMAND_NOT_ALLOWLISTED")
    if body.timeout<1 or body.timeout>120:
        raise HTTPException(400,"INVALID_TIMEOUT")
    cwd=safe_path(body.cwd)
    try:
        p=subprocess.run(body.command,cwd=str(cwd),capture_output=True,text=True,timeout=body.timeout)
        return {"ok":p.returncode==0,"returncode":p.returncode,"stdout":p.stdout[-MAX_OUTPUT:],"stderr":p.stderr[-MAX_OUTPUT:]}
    except subprocess.TimeoutExpired:
        return {"ok":False,"error":"TIMEOUT"}

@app.post("/write")
def write(token:str,path:str,content:str):
    auth(token)
    q=safe_path(path)
    q.parent.mkdir(parents=True,exist_ok=True)
    q.write_text(content,encoding="utf-8")
    return {"ok":True,"path":str(q.relative_to(SANDBOX))}

@app.get("/read")
def read(token:str,path:str):
    auth(token)
    q=safe_path(path)
    if not q.is_file(): raise HTTPException(404,"FILE_NOT_FOUND")
    return {"ok":True,"path":str(q.relative_to(SANDBOX)),"content":q.read_text(encoding="utf-8")}

@app.get("/status")
def status(token:str):
    auth(token)
    return {"ok":True,"sandbox":str(SANDBOX),"allowed_commands":sorted(ALLOWED_COMMANDS)}
