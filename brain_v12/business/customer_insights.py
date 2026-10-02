"""Customer insight memory based on explicit evidence."""
from __future__ import annotations

def summarize(signals: list[dict]) -> dict:
    problems={}
    for s in signals:
        p=s.get("problem","").strip()
        if p:
            problems[p]=problems.get(p,0)+1
    return {"signal_count":len(signals),"problem_frequency":problems}
