"""Research ledger for factual and sensitive productions."""
from __future__ import annotations
from pathlib import Path
import json,time
class ResearchLedger:
    def __init__(self,path="research_ledger.json"):
        self.path=Path(path); self.items=self._load()
    def _load(self):
        if self.path.exists():
            try:return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:pass
        return {"version":1,"claims":[]}
    def add_claim(self,claim:str,source:str,status:str="UNVERIFIED"):
        self.items["claims"].append({"claim":claim,"source":source,"status":status,"time":time.time()})
        self.save()
    def unresolved(self): return [x for x in self.items["claims"] if x.get("status")!="VERIFIED"]
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(self.items,ensure_ascii=False,indent=2),encoding="utf-8")
