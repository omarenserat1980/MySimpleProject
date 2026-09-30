"""Evidence-based adaptive backend selection for Brain.

The router learns only from explicit execution observations. Health and policy
gates remain authoritative; learning can reorder compatible backends but cannot
activate an unavailable or forbidden backend.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable

def load_observations(path: str = "brain6_artifacts/backend_observations.jsonl") -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    rows=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row=json.loads(line)
            if isinstance(row,dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows[-500:]

def record_observation(backend_id: str, task: str, success: bool,
                       latency_ms: float | None = None,
                       path: str = "brain6_artifacts/backend_observations.jsonl") -> dict:
    p=Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    row={"backend":backend_id,"task":task,"success":bool(success)}
    if latency_ms is not None:
        row["latency_ms"]=float(latency_ms)
    with p.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False)+"\n")
    return row

def score(backend_id: str, task: str, observations: Iterable[dict]) -> float:
    rows=[x for x in observations if x.get("backend")==backend_id and x.get("task")==task]
    if not rows:
        return 0.5
    # Recent bounded evidence gets more weight without allowing one event to dominate.
    recent=rows[-20:]
    successes=sum(1 for x in recent if x.get("success") is True)
    return (successes + 1.0) / (len(recent) + 2.0)

def rank(candidates: list[dict], task: str, observations: Iterable[dict]) -> list[dict]:
    ranked=[]
    for index, candidate in enumerate(candidates):
        item=dict(candidate)
        item["learned_score"]=round(score(candidate["id"],task,observations),4)
        item["_order"]=index
        ranked.append(item)
    ranked.sort(key=lambda x:(-x["learned_score"],x["_order"]))
    for item in ranked:
        item.pop("_order",None)
    return ranked
