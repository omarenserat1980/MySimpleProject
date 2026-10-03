"""Brain Git file browser; reads only Brain-owned repository data."""
from __future__ import annotations
from pathlib import Path
class BrainGitFileBrowser:
    def __init__(self,service): self.service=service
    def tree(self,name,ref="HEAD",prefix=""):
        repo=self.service._path(name)
        args=["ls-tree","-r","--name-only",ref]
        if prefix:
            args.extend(["--",prefix])
        out=self.service._run(args,cwd=repo)
        return [x for x in out.splitlines() if x]
    def file(self,name,path,ref="HEAD"):
        return {"repository":name,"path":path,"ref":ref,"content":self.service.read_file_at(name,path,ref)}
