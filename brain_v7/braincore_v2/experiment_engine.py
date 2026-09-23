"""Bounded experiment engine: turn hypotheses into measurable tests."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import json,os,time,uuid
from pathlib import Path
PATH=Path(os.getenv("BRAIN_EXPERIMENT_PATH","experiments.json"))
@dataclass(frozen=True)
class Experiment:
    id:str
    hypothesis:str
    metric:str
    target:float
    max_cost_jod:float=0.0
    status:str="PLANNED"
def _load():
    try:
        x=json.loads(PATH.read_text(encoding="utf-8")); return x if isinstance(x,dict) else {}
    except Exception:return {}
def _save(x):
    PATH.parent.mkdir(parents=True,exist_ok=True); PATH.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
def create(hypothesis:str,metric:str,target:float,max_cost_jod:float=0.0)->dict:
    if max_cost_jod<0: raise ValueError("NEGATIVE_COST")
    e=Experiment(uuid.uuid4().hex[:12],hypothesis,metric,float(target),float(max_cost_jod))
    d=_load(); d.setdefault("experiments",[]).append(asdict(e)); _save(d); return asdict(e)
def complete(experiment_id:str,value:float,evidence:str)->dict:
    if not evidence.strip(): raise ValueError("EVIDENCE_REQUIRED")
    d=_load()
    for e in d.get("experiments",[]):
        if e["id"]==experiment_id:
            e.update({"status":"COMPLETED","value":float(value),"evidence":evidence,"completed_at":time.time()})
            _save(d); return e
    raise KeyError("EXPERIMENT_NOT_FOUND")
def summary()->dict:
    rows=_load().get("experiments",[])
    return {"total":len(rows),"completed":sum(x.get("status")=="COMPLETED" for x in rows),
            "planned":sum(x.get("status")=="PLANNED" for x in rows)}
