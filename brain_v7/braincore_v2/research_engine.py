"""Research/evidence engine for autonomous development and market learning.
It stores sourced observations and keeps hypotheses separate from verified facts.
"""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
from typing import Any,Iterable
PATH=Path(os.getenv("BRAIN_RESEARCH_PATH","research_memory.json"))
def _load():
    try:
        x=json.loads(PATH.read_text(encoding="utf-8")); return x if isinstance(x,dict) else {}
    except Exception: return {}
def _save(x):
    PATH.parent.mkdir(parents=True,exist_ok=True); PATH.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
def add_observation(topic:str,claim:str,source_url:str,source_type:str="web",verified:bool=False)->dict[str,Any]:
    if not str(topic).strip() or not str(claim).strip() or not str(source_url).strip():
        raise ValueError("TOPIC_CLAIM_SOURCE_REQUIRED")
    key=hashlib.sha256((topic+"|"+claim+"|"+source_url).encode()).hexdigest()[:20]
    item={"id":key,"topic":str(topic),"claim":str(claim),"source_url":str(source_url),
          "source_type":str(source_type),"verified":bool(verified),"ts":time.time()}
    data=_load(); items=data.setdefault("observations",[])
    if not any(x.get("id")==key for x in items): items.append(item)
    _save(data); return item
def search_memory(topic:str)->list[dict[str,Any]]:
    t=str(topic).lower()
    return [x for x in _load().get("observations",[]) if t in str(x.get("topic","")).lower() or t in str(x.get("claim","")).lower()]
def verified_facts(topic:str|None=None)->list[dict[str,Any]]:
    rows=[x for x in _load().get("observations",[]) if x.get("verified") is True]
    if topic: rows=[x for x in rows if str(topic).lower() in (str(x.get("topic",""))+" "+str(x.get("claim",""))).lower()]
    return rows
def snapshot()->dict[str,Any]:
    rows=_load().get("observations",[])
    return {"observations":len(rows),"verified":sum(bool(x.get("verified")) for x in rows),
            "topics":sorted({str(x.get("topic")) for x in rows})}
