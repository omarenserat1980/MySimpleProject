"""Safe PowerShell-like emulator for Brain Digital Twins.

This is a deterministic command interpreter, not a Windows shell. It never
launches PowerShell and never crosses the emulator sandbox boundary.
"""
from __future__ import annotations
from dataclasses import dataclass
import json, re, time
from pathlib import Path
from typing import Any
from .desktop_commander_emulator import DesktopCommanderEmulator

SCHEMA="brain.powershell-emulator.v1"

@dataclass(frozen=True)
class PowerShellPolicy:
    max_commands:int=32
    max_output_bytes:int=65536
    allow_mutation:bool=True

class PowerShellEmulator:
    def __init__(self, desktop:DesktopCommanderEmulator, *, policy:PowerShellPolicy|None=None):
        self.desktop=desktop
        self.policy=policy or PowerShellPolicy()
        self.env={"COMPUTERNAME":desktop.node_id,"OS":"BRAIN-VIRTUAL-WINDOWS","PS_VERSION":"7.5-EMU"}
        self.cwd="."
        self.history:list[str]=[]

    def info(self)->dict[str,Any]:
        return {"ok":True,"schema":SCHEMA,"mode":"SIMULATED","shell":"PowerShell-Emulator",
                "commands":["Get-Location","Get-ChildItem","Get-Content","Set-Content",
                            "New-Item","Remove-Item","Get-Process","Get-Command",
                            "Get-ComputerInfo","Get-Environment","Write-Output","Set-Location"]}

    def run(self, script:str)->dict[str,Any]:
        parts=[x.strip() for x in re.split(r";|\n",script) if x.strip()]
        if len(parts)>self.policy.max_commands:
            return {"ok":False,"status":"COMMAND_LIMIT_EXCEEDED","reality":"SIMULATED"}
        out=[]; errors=[]
        for command in parts:
            self.history.append(command)
            try:
                r=self._command(command)
                if r.get("output") is not None: out.append(r["output"])
                if not r.get("ok"): errors.append(r)
            except Exception as e:
                errors.append({"ok":False,"status":"EMULATOR_ERROR","error":f"{type(e).__name__}:{e}"})
        text="\n".join(str(x) for x in out)
        text=text[:self.policy.max_output_bytes]
        return {"ok":not errors,"status":"COMPLETED" if not errors else "COMMAND_FAILED",
                "output":text,"errors":errors,"commands":len(parts),
                "reality":"SIMULATED","source":"powershell-emulator"}

    def _command(self,c:str)->dict[str,Any]:
        toks=re.findall(r'(?:"[^"]*"|\'[^\']*\'|[^\s]+)',c)
        if not toks:return {"ok":False,"status":"COMMAND_REQUIRED"}
        name=toks[0].lower().lstrip("-")
        args=toks[1:]
        if name in {"get-location","pwd"}: return {"ok":True,"output":self.cwd}
        if name in {"set-location","cd"}:
            path=self._arg(args)
            target=(self.desktop.root / self.cwd / path).resolve()
            if target != self.desktop.root and self.desktop.root not in target.parents:
                return {"ok":False,"status":"PATH_ESCAPE_DENIED"}
            if not target.is_dir(): return {"ok":False,"status":"PATH_NOT_FOUND"}
            self.cwd="." if target == self.desktop.root else target.relative_to(self.desktop.root).as_posix()
            return {"ok":True,"output":self.cwd}
        if name in {"get-childitem","gci","dir","ls"}:
            r=self.desktop.list_dir(self._arg(args) if args else self.cwd)
            if not r.get("ok"): return r
            return {"ok":True,"output":"\n".join(i["name"] for i in r["items"])}
        if name in {"get-content","cat","type"}:
            r=self.desktop.read_file(self._arg(args))
            return {"ok":r.get("ok"),"output":r.get("content",""),"status":r.get("status")}
        if name=="write-output":
            return {"ok":True,"output":" ".join(self._clean(a) for a in args)}
        if name=="get-command":
            q=self._clean(self._arg(args)).lower() if args else ""
            cmds=self.info()["commands"]
            return {"ok":True,"output":"\n".join(x for x in cmds if q in x.lower())}
        if name=="get-computerinfo":
            return {"ok":True,"output":json.dumps({"ComputerName":self.desktop.node_id,"OsName":"BRAIN Virtual Windows","OsArchitecture":"x64","Reality":"SIMULATED"},sort_keys=True)}
        if name=="get-environment":
            return {"ok":True,"output":"\n".join(f"{k}={v}" for k,v in sorted(self.env.items()))}
        if name=="get-process":
            return {"ok":True,"output":json.dumps(self.desktop.process_snapshot()["processes"],sort_keys=True)}
        if name=="new-item":
            if not self.policy.allow_mutation:return {"ok":False,"status":"MUTATION_DISABLED"}
            path=self._target_path(args)
            typ="directory" if any("directory" in a.lower() for a in args) else "file"
            if typ=="directory":r=self.desktop.mkdir(path)
            else:r=self.desktop.write_file(path,"")
            return {"ok":r.get("ok"),"output":path,"status":r.get("status")}
        if name=="set-content":
            if not self.policy.allow_mutation:return {"ok":False,"status":"MUTATION_DISABLED"}
            path=self._arg(args); match=re.search(r"-Value\s+(.+)$",c,re.I)
            content=self._clean(match.group(1)) if match else ""
            r=self.desktop.write_file(path,content)
            return {"ok":r.get("ok"),"output":path,"status":r.get("status")}
        if name=="remove-item":
            if not self.policy.allow_mutation:return {"ok":False,"status":"MUTATION_DISABLED"}
            r=self.desktop.delete(self._arg(args)); return {"ok":r.get("ok"),"output":"" if r.get("ok") else None,"status":r.get("status")}
        return {"ok":False,"status":"COMMAND_NOT_SUPPORTED","command":toks[0]}

    @staticmethod
    def _clean(x:str)->str:
        x=x.strip()
        if len(x)>=2 and x[0] in "'\"" and x[-1]==x[0]:return x[1:-1]
        return x

    def _arg(self,args:list[str])->str:
        for a in args:
            if not a.startswith("-"):return self._clean(a)
        return "."

    def _target_path(self,args:list[str])->str:
        values=[self._clean(a) for a in args if not a.startswith("-")]
        return values[-1] if values else "."

__all__=["PowerShellPolicy","PowerShellEmulator","SCHEMA"]
