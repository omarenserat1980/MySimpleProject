"""Evidence-based learning memory with bounded, decaying confidence."""
from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Any
PATH=Path(os.getenv("BRAIN_LEARNING_PATH","learning_memory.json"))
HALF_LIFE_DAYS=30.0
def _load():
    try:
        x=json.loads(PATH.read_text(encoding="utf-8")); return x if isinstance(x,dict) else {}
    except Exception: return {}
def _save(data):
    PATH.parent.mkdir(parents=True,exist_ok=True); PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
def record(domain:str,claim:str,*,passed:bool,evidence:str,source:str="runtime"):
    if not str(evidence).strip(): raise ValueError("EVIDENCE_REQUIRED")
    item={"domain":str(domain),"claim":str(claim),"passed":bool(passed),"evidence":str(evidence),"source":str(source),"ts":time.time()}
    data=_load(); data.setdefault("items",[]).append(item); _save(data); return item
def confidence(domain:str,claim:str|None=None)->float:
    now=time.time(); weighted=0.0; total=0.0
    for x in _load().get("items",[]):
        if x.get("domain")!=domain or (claim is not None and x.get("claim")!=claim): continue
        age=max(0.0,(now-float(x.get("ts",now)))/86400.0); w=0.5**(age/HALF_LIFE_DAYS)
        total+=w; weighted+=(1.0 if x.get("passed") else 0.0)*w
    return round(weighted/total,4) if total else 0.0
def snapshot()->dict[str,Any]:
    items=_load().get("items",[]); domains=sorted({str(x.get("domain")) for x in items})
    return {"records":len(items),"domains":domains,"confidence":{d:confidence(d) for d in domains}}
