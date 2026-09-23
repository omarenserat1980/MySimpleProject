"""Tamper-evident audit chain for financial events."""
from __future__ import annotations
import hashlib,json
def event_hash(event:dict,previous_hash:str="")->str:
    payload=json.dumps({"event":event,"previous_hash":previous_hash},sort_keys=True,separators=(",",":"))
    return hashlib.sha256(payload.encode()).hexdigest()
def append(chain:list[dict],event:dict)->dict:
    previous=chain[-1]["hash"] if chain else ""
    item={"event":event,"previous_hash":previous,"hash":event_hash(event,previous)}
    chain.append(item); return item
def verify(chain:list[dict])->bool:
    previous=""
    for item in chain:
        if item.get("previous_hash")!=previous or item.get("hash")!=event_hash(item["event"],previous): return False
        previous=item["hash"]
    return True
