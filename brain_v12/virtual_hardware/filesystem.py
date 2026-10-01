from __future__ import annotations
import hashlib
from dataclasses import dataclass

@dataclass(frozen=True)
class VirtualFile:
    path:str
    data:bytes

class VirtualFilesystem:
    """Deterministic filesystem facade backed by VirtualStorage."""
    def __init__(self,storage):
        self.storage=storage

    def normalize(self,path:str)->str:
        parts=[x for x in str(path).split("/") if x]
        if ".." in parts: raise ValueError("PATH_TRAVERSAL")
        return "/" + "/".join(parts)

    def write(self,path:str,data:bytes|str):
        p=self.normalize(path)
        raw=data.encode() if isinstance(data,str) else bytes(data)
        self.storage.write(p,raw)
        return {"ok":True,"path":p,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}

    def read(self,path:str)->bytes:
        return self.storage.read(self.normalize(path))

    def exists(self,path:str)->bool:
        return self.normalize(path) in self.storage.files

    def list(self,prefix:str="/"):
        p=self.normalize(prefix)
        return sorted(k for k in self.storage.files if k.startswith(p))

    def manifest(self):
        return self.storage.manifest()
