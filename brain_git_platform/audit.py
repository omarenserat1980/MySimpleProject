from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
from .service import ROOT

class AuditLog:
    def __init__(self, root: Path | None = None):
        self.path=(root or ROOT)/"audit.jsonl"
        self.path.parent.mkdir(parents=True,exist_ok=True)

    def record(self, actor:str, action:str, resource:str, outcome:str="success", metadata:dict|None=None):
        event={
            "timestamp":datetime.now(timezone.utc).isoformat(),
            "actor":actor,"action":action,"resource":resource,
            "outcome":outcome,"metadata":metadata or {}
        }
        with self.path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(event,ensure_ascii=False,sort_keys=True)+"\n")
        return event
