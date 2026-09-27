"""Director-level scheduler: chooses the next useful production action."""
from __future__ import annotations
from typing import Any
from .task_stack import TaskStack

def seed_tasks(stack:TaskStack,shots:list[dict]):
    for s in shots:
        sid=s["shot_id"]
        deps=[]
        idx=int(sid.rsplit("_",1)[-1]) if sid.rsplit("_",1)[-1].isdigit() else 0
        if idx>1: deps=[f"shot_{idx-1:03d}"]
        stack.add(sid,"GENERATE_SHOT",priority=100-int(s.get("scene_id",1)),depends_on=deps,payload={"shot":s})
    return stack

def choose_next(stack:TaskStack, runtime:dict[str,Any]|None=None)->dict[str,Any]:
    task=stack.next()
    if not task:return {"status":"IDLE","reason":"no_ready_tasks"}
    return {"status":"DISPATCH","task":task,"runtime":runtime or {}}
