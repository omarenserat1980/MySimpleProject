"""Defensive security event correlation."""
from __future__ import annotations
from collections import Counter
def correlate(events:list[dict])->dict:
    types=Counter(e.get("type","unknown") for e in events)
    critical=[e for e in events if e.get("severity")=="critical"]
    return {"event_count":len(events),"by_type":dict(types),
            "critical_count":len(critical),
            "incident_required":bool(critical) or len(events)>=20}
