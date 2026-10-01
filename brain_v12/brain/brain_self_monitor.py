"""Brain self-monitor: health/evidence checks exposed to Brain itself."""
from __future__ import annotations
import os, subprocess, time
class BrainSelfMonitor:
    def __init__(self, root=None):
        self.root=root or os.getcwd()
    def _check(self, name, fn):
        try:
            value=fn()
            return {"name":name,"ok":bool(value),"detail":value}
        except Exception as e:
            return {"name":name,"ok":False,"detail":str(e)}
    def snapshot(self):
        checks=[
            self._check("brain_root",lambda: os.path.isdir(os.path.join(self.root,"brain_v12"))),
            self._check("brain_git",lambda: os.path.isdir(os.path.join(self.root,"brain_v12","brain_git"))),
            self._check("supervisor",lambda: os.path.isfile(os.path.join(self.root,"brain_v12","brain","brain_supervisor.py"))),
            self._check("git_repository",lambda: subprocess.run(["git","rev-parse","--is-inside-work-tree"],cwd=self.root,text=True,capture_output=True).returncode==0),
        ]
        ok=all(x["ok"] for x in checks)
        return {"ok":ok,"status":"HEALTHY" if ok else "DEGRADED","timestamp":time.time(),"checks":checks}
