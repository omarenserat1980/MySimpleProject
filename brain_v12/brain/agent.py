import os
import pathlib
import platform
import subprocess

class Agent:
    def __init__(self):
        self.sandbox=pathlib.Path(os.getenv("AGENT_SANDBOX","./agent_sandbox")).resolve()
        self.sandbox.mkdir(parents=True,exist_ok=True)
        self.allowed=set(filter(None,os.getenv("AGENT_COMMANDS","python,python3,pytest,git").split(",")))

    def status(self):
        return {"ok":True,"platform":platform.platform(),"sandbox":str(self.sandbox),"allowed_commands":sorted(self.allowed)}

    def execute(self,command,cwd=".",timeout=30):
        if not command or command[0] not in self.allowed:
            return {"ok":False,"error":"COMMAND_NOT_ALLOWLISTED"}
        if timeout<1 or timeout>120:
            return {"ok":False,"error":"INVALID_TIMEOUT"}
        p=(self.sandbox/pathlib.Path(cwd)).resolve()
        if p!=self.sandbox and self.sandbox not in p.parents:
            return {"ok":False,"error":"PATH_OUTSIDE_SANDBOX"}
        try:
            r=subprocess.run(command,cwd=str(p),capture_output=True,text=True,timeout=timeout)
            return {"ok":r.returncode==0,"returncode":r.returncode,"stdout":r.stdout[-12000:],"stderr":r.stderr[-12000:]}
        except subprocess.TimeoutExpired:
            return {"ok":False,"error":"TIMEOUT"}
