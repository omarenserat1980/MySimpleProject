"""Evidence quality and freshness scoring for market intelligence."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class Evidence:
    claim:str
    source:str
    source_type:str="unknown"
    verified:bool=False
    observed_at:str|None=None

TRUST={"official":1.0,"primary":.95,"reputable":.85,"marketplace":.65,"secondary":.55,"unknown":.25}

def score(e:Evidence)->float:
    s=TRUST.get(e.source_type,TRUST["unknown"])
    if not e.verified: s*=.55
    if e.observed_at:
        try:
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(e.observed_at.replace("Z","+00:00"))).days
            s*=max(.25,1-min(age,365)/730)
        except ValueError: s*=.8
    return round(s,4)
