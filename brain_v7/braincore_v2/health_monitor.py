"""Runtime health checks and fail-safe state."""
from __future__ import annotations
import time
from .governance import policy_snapshot
def check()->dict:
    p=policy_snapshot()
    return {"timestamp":time.time(),"healthy":all(v is False for k,v in p.items() if k!="audit_chain"),
            "policy":p,"checks":["policy","bounded-autonomy","audit-chain"]}
def can_continue()->bool:
    return bool(check()["healthy"])
