"""BRAIN Desktop Commander Emulator.

A safe, deterministic virtual desktop node. It models the useful remote-control
surface without pretending to be a real machine: filesystem, processes,
heartbeat, capabilities and append-only audit records.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, os, shlex, subprocess, threading, time, uuid
from typing import Any

SCHEMA="brain.desktop-commander-emulator.v1"

@dataclass(frozen=True)
class EmulatorPolicy:
    root: Path
    max_output_bytes: int = 65536
    command_timeout_seconds: float = 20.0
    allow_shell: bool = False

class DesktopCommanderEmulator:
    def __init__(self, root: str|Path, *, node_id="brain-desktop-emu-01", policy: EmulatorPolicy|None=None):
        self.node_id=node_id
        self.policy=policy or EmulatorPolicy(Path(root))
        self.root=self.policy.root.resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self._lock=threading.RLock()
        self._processes:dict[str,subprocess.Popen[str]]={}
        self._process_started:dict[str,float]={}
        self._audit_path=self.root/".brain"/"audit.jsonl"
        self._audit_path.parent.mkdir(parents=True,exist_ok=True)

    def _safe(self, path:str|Path)->Path:
        p=(self.root/Path(path)).resolve()
        if p!=self.root and self.root not in p.parents:
            raise PermissionError("EMULATOR_PATH_ESCAPE")
        return p

    def _audit(self, action:str, payload:dict[str,Any])->None:
        rec={"ts":time.time(),"node_id":self.node_id,"action":action,"payload":payload}
        with self._audit_path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(rec,sort_keys=True,separators=(",",":"))+"\n")

    def info(self)->dict[str,Any]:
        return {"ok":True,"schema":SCHEMA,"node_id":self.node_id,"platform":"BRAIN-VIRTUAL-DESKTOP",
                "reality":"SIMULATED","execution_scope":"LOCAL_SANDBOX_ONLY",
                "capabilities":["filesystem","process","heartbeat","audit"],
                "policy":{"allow_shell":self.policy.allow_shell,
                          "command_timeout_seconds":self.policy.command_timeout_seconds,
                          "max_output_bytes":self.policy.max_output_bytes},
                "sandbox":str(self.root)}

    def heartbeat(self,metadata:dict[str,Any]|None=None)->dict[str,Any]:
        r={"ok":True,"node_id":self.node_id,"ts":time.time(),"state":"ONLINE","metadata":metadata or {}}
        self._audit("heartbeat",r); return r

    def mkdir(self,path:str)->dict[str,Any]:
        p=self._safe(path); p.mkdir(parents=True,exist_ok=True); self._audit("mkdir",{"path":str(path)})
        return {"ok":True,"path":str(p.relative_to(self.root))}

    def write_file(self,path:str,content:str)->dict[str,Any]:
        p=self._safe(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8")
        self._audit("write_file",{"path":str(path),"bytes":len(content.encode())})
        return {"ok":True,"path":str(p.relative_to(self.root)),"bytes":len(content.encode())}

    def read_file(self,path:str)->dict[str,Any]:
        p=self._safe(path)
        if not p.is_file(): return {"ok":False,"status":"FILE_NOT_FOUND"}
        data=p.read_bytes()[:self.policy.max_output_bytes]
        return {"ok":True,"path":str(p.relative_to(self.root)),"content":data.decode("utf-8",errors="replace"),
                "truncated":p.stat().st_size>len(data)}

    def list_dir(self,path:str=".")->dict[str,Any]:
        p=self._safe(path)
        if not p.is_dir(): return {"ok":False,"status":"DIRECTORY_NOT_FOUND"}
        items=[{"name":x.name,"type":"dir" if x.is_dir() else "file","size":x.stat().st_size if x.is_file() else None} for x in sorted(p.iterdir(),key=lambda x:x.name.lower())]
        return {"ok":True,"path":str(p.relative_to(self.root)),"items":items}

    def delete(self,path:str)->dict[str,Any]:
        p=self._safe(path)
        if p==self.root: raise PermissionError("EMULATOR_ROOT_DELETE_FORBIDDEN")
        if p.is_dir(): p.rmdir()
        elif p.exists(): p.unlink()
        else: return {"ok":False,"status":"PATH_NOT_FOUND"}
        self._audit("delete",{"path":str(path)}); return {"ok":True}

    def start_process(self, command:str, *, cwd:str=".", env:dict[str,str]|None=None)->dict[str,Any]:
        if not self.policy.allow_shell: return {"ok":False,"status":"SHELL_DISABLED"}
        work=self._safe(cwd)
        if not work.is_dir(): return {"ok":False,"status":"WORKING_DIRECTORY_NOT_FOUND"}
        if self.policy.command_timeout_seconds <= 0:
            return {"ok":False,"status":"INVALID_COMMAND_TIMEOUT"}
        args=shlex.split(command)
        if not args: return {"ok":False,"status":"COMMAND_REQUIRED"}
        clean_env={}
        for key,value in (env or {}).items():
            if not isinstance(key,str) or not isinstance(value,str) or "=" in key or chr(0) in key or chr(0) in value:
                return {"ok":False,"status":"INVALID_ENVIRONMENT"}
            clean_env[key]=value
        try:
            proc=subprocess.Popen(args,cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  env={**os.environ,**clean_env})
        except OSError as exc:
            return {"ok":False,"status":"PROCESS_START_FAILED","error_type":type(exc).__name__}
        pid=uuid.uuid4().hex
        with self._lock:
            self._processes[pid]=proc
            self._process_started[pid]=time.monotonic()
        self._audit("start_process",{"process_id":pid,"command":args,"cwd":cwd,
                                     "reality":"SIMULATED","timeout_seconds":self.policy.command_timeout_seconds})
        return {"ok":True,"process_id":pid,"pid":proc.pid,"status":"RUNNING","reality":"SIMULATED"}

    def read_process_output(self,process_id:str,timeout:float=0.2)->dict[str,Any]:
        with self._lock: proc=self._processes.get(process_id)
        if proc is None:return {"ok":False,"status":"PROCESS_NOT_FOUND"}
        with self._lock:
            started=self._process_started.get(process_id,time.monotonic())
        remaining=self.policy.command_timeout_seconds-(time.monotonic()-started)
        if remaining <= 0:
            proc.kill()
            out,_=proc.communicate()
            self._forget_process(process_id)
            self._audit("process_timeout",{"process_id":process_id,"timeout_seconds":self.policy.command_timeout_seconds})
            output=out or ""
            return {"ok":False,"status":"TIMED_OUT","process_id":process_id,
                    "returncode":proc.returncode,"output":output[:self.policy.max_output_bytes],
                    "truncated":len(output)>self.policy.max_output_bytes,"reality":"SIMULATED"}
        try:
            out,_=proc.communicate(timeout=min(max(0.0,timeout),remaining))
        except subprocess.TimeoutExpired:
            if time.monotonic()-started >= self.policy.command_timeout_seconds:
                proc.kill()
                out,_=proc.communicate()
                self._forget_process(process_id)
                self._audit("process_timeout",{"process_id":process_id,"timeout_seconds":self.policy.command_timeout_seconds})
                output=out or ""
                return {"ok":False,"status":"TIMED_OUT","process_id":process_id,
                        "returncode":proc.returncode,"output":output[:self.policy.max_output_bytes],
                        "truncated":len(output)>self.policy.max_output_bytes,"reality":"SIMULATED"}
            return {"ok":True,"status":"RUNNING","process_id":process_id,"reality":"SIMULATED"}
        self._forget_process(process_id)
        output=out or ""
        return {"ok":True,"status":"COMPLETED","process_id":process_id,"returncode":proc.returncode,
                "output":output[:self.policy.max_output_bytes],
                "truncated":len(output)>self.policy.max_output_bytes,"reality":"SIMULATED"}

    def _forget_process(self,process_id:str)->None:
        with self._lock:
            self._processes.pop(process_id,None)
            self._process_started.pop(process_id,None)

    def stop_process(self,process_id:str)->dict[str,Any]:
        """Stop a sandbox process and reap it so it cannot leak in the emulator registry."""
        with self._lock:
            proc=self._processes.get(process_id)
        if proc is None:return {"ok":False,"status":"PROCESS_NOT_FOUND"}
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1.0)
            # Drain captured output after the process has exited; bounded before returning.
            output,_=proc.communicate(timeout=1.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            output,_=proc.communicate()
        finally:
            self._forget_process(process_id)
        text_output=output or ""
        self._audit("stop_process",{"process_id":process_id,"returncode":proc.returncode,
                                    "reality":"SIMULATED","output_truncated":len(text_output)>self.policy.max_output_bytes})
        return {"ok":True,"status":"STOPPED","process_id":process_id,"returncode":proc.returncode,
                "output":text_output[:self.policy.max_output_bytes],
                "truncated":len(text_output)>self.policy.max_output_bytes,"reality":"SIMULATED"}

    def process_snapshot(self)->dict[str,Any]:
        with self._lock:
            return {"ok":True,"reality":"SIMULATED","processes":[{"process_id":k,"pid":v.pid,"running":v.poll() is None} for k,v in self._processes.items()]}

    def audit(self,limit:int=100)->dict[str,Any]:
        if not self._audit_path.exists():return {"ok":True,"records":[]}
        rows=self._audit_path.read_text(encoding="utf-8").splitlines()[-max(1,int(limit)):]
        return {"ok":True,"records":[json.loads(x) for x in rows]}
