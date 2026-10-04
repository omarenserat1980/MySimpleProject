"""Deterministic evidence manifest for BRAIN film exports."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def build(master,project,qc,release):
    p=Path(master)
    return {"version":1,"master":str(p),"sha256":sha256(p) if p.exists() else None,"project":project,"qc":qc,"release":release}
if __name__=="__main__":
    import sys
    print(json.dumps(build(sys.argv[1],{}, {}, {"status":"BLOCKED"}),indent=2))
