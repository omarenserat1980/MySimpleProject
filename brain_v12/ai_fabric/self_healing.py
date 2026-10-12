from __future__ import annotations
from time import monotonic

def repair_execute(fabric, task, payload, kind="model"):
    """Run bounded self-healing; each attempt uses learned ranking and records evidence."""
    attempts = []
    for attempt_no in range(1, max(1, fabric.policy.max_attempts) + 1):
        result = fabric.execute(task, payload, kind)
        attempts.append({"attempt": attempt_no, "result": result})
        if result.get("ok"):
            return {
                "ok": True,
                "status": "SELF_HEALING_VERIFIED",
                "attempts": attempts,
                "selected": result.get("capability"),
                "evidence": result.get("evidence"),
            }
    return {
        "ok": False,
        "status": "SELF_HEALING_EXHAUSTED",
        "attempts": attempts,
        "evidence": attempts[-1].get("result", {}).get("evidence") if attempts else None,
    }
