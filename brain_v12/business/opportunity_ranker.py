"""Evidence-first opportunity ranking and deduplication."""
from __future__ import annotations
import hashlib

def fingerprint(item: dict) -> str:
    raw="|".join(str(item.get(k,"")).strip().lower() for k in ("customer_hint","problem","source"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def score(item: dict) -> int:
    score=0
    if item.get("problem"): score += 30
    if item.get("evidence_url") or item.get("evidence"): score += 30
    if item.get("customer_hint"): score += 15
    if item.get("location"): score += 5
    if item.get("offer_matches"): score += min(20, 5*len(item["offer_matches"]))
    return min(100, score)

def rank(items: list[dict]) -> list[dict]:
    seen=set()
    output=[]
    for item in items:
        fp=fingerprint(item)
        if fp in seen:
            continue
        seen.add(fp)
        enriched=dict(item)
        enriched["fingerprint"]=fp
        enriched["evidence_score"]=score(enriched)
        output.append(enriched)
    return sorted(output,key=lambda x:x["evidence_score"],reverse=True)
