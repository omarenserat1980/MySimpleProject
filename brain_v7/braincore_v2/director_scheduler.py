"""Director-level dependency-aware scheduler optimized for throughput."""
from __future__ import annotations
from typing import Any
from .task_stack import TaskStack

def seed_tasks(stack: TaskStack, shots: list[dict]):
    for index, shot in enumerate(shots):
        sid = shot["shot_id"]
        generation = shot.get("generation") or {}
        policy = str(generation.get("continuity_policy") or "")
        # Only continuity-dependent shots wait. Establishing shots and first
        # shots of a scene remain independent so different scenes can render
        # concurrently.
        deps: list[str] = []
        if index > 0 and (not policy or policy in {"identity_first", "match_cut"}):
            prev = shots[index - 1]
            if prev.get("scene_id") == shot.get("scene_id"):
                deps = [prev["shot_id"]]
        priority = int(1000 - index)
        if shot.get("purpose") in {"Immediate attention", "Create tension and relevance"}:
            priority += 50
        stack.add(
            sid,
            "GENERATE_SHOT",
            priority=priority,
            depends_on=deps,
            payload={"shot": shot, "continuity_dependency": deps},
        )
    return stack

def choose_next(stack: TaskStack, runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    task = stack.next()
    if not task:
        return {"status": "IDLE", "reason": "no_ready_tasks"}
    return {"status": "DISPATCH", "task": task, "runtime": runtime or {}}
