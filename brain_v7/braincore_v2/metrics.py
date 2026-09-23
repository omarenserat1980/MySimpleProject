"""Small operational metrics layer."""
from __future__ import annotations
import json,os
from pathlib import Path
PATH=Path(os.getenv("BRAIN_METRICS_PATH","brain_metrics.json"))
def record(name:str,value:float,unit:str="count")->dict:
    PATH.parent.mkdir(parents=True,exist_ok=True)
    try:d=json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:d={}
    row={"name":name,"value":float(value),"unit":unit}
    d.setdefault("metrics",[]).append(row); PATH.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8"); return row
def latest(name:str):
    try:d=json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:return None
    rows=[x for x in d.get("metrics",[]) if x.get("name")==name]
    return rows[-1] if rows else None
