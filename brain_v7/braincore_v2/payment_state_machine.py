"""Explicit payment lifecycle; impossible states are rejected."""
from __future__ import annotations
TRANSITIONS={
"CREATED":{"APPROVAL_REQUIRED","CANCELLED"},
"APPROVAL_REQUIRED":{"SUBMITTED","CANCELLED"},
"SUBMITTED":{"PENDING","FAILED","CANCELLED"},
"PENDING":{"CONFIRMED","FAILED","REVERSED"},
"CONFIRMED":{"REVERSED"},
"FAILED":set(),"CANCELLED":set(),"REVERSED":set(),
}
def transition(current:str,nxt:str)->str:
    if nxt not in TRANSITIONS.get(current,set()):
        raise ValueError(f"invalid transition {current}->{nxt}")
    return nxt
