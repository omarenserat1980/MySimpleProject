from __future__ import annotations

def repair_execute(fabric, task, payload, kind="model"):
    attempts=[]
    for _ in range(max(1, fabric.policy.max_attempts)):
        result=fabric.execute(task,payload,kind)
        attempts.append(result)
        if result.get("ok"):
            return {"ok":True,"status":"SELF_HEALING_VERIFIED","attempts":attempts,"result":result}
    return {"ok":False,"status":"SELF_HEALING_EXHAUSTED","attempts":attempts}
