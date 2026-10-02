#!/usr/bin/env python3
"""Continuous Brain supervisor: choose -> think -> act -> verify -> learn -> repeat.

The supervisor keeps producing bounded work from goals, pending tasks, failures and
future-evolution predictions. Safety gates remain authoritative; continuity is not
permission to bypass them.
"""
from __future__ import annotations
import json, os, time, urllib.parse, urllib.request
from pathlib import Path

BASE = os.environ.get("V12_BRAIN_URL", "http://127.0.0.1:8012").rstrip("/")
CONTROL = os.environ.get("BRAIN_CONTROL_KEY", "")
INTERVAL = max(15, int(os.environ.get("BRAIN_SUPERVISOR_INTERVAL", "60")))
ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
HISTORY = STATE / "continuous_supervisor.jsonl"

def request(method, path, headers=None, payload=None):
    data = None
    h = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def record(row):
    STATE.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), **row}, ensure_ascii=False) + "\n")

def recent_fingerprints(limit=30):
    if not HISTORY.exists():
        return set()
    rows = HISTORY.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]
    return {json.loads(x).get("fingerprint") for x in rows if x.strip()}

def candidates():
    items = []
    try:
        goals = request("GET", "/api/goals")
        for g in goals if isinstance(goals, list) else goals.get("goals", []):
            text = str(g.get("text", "")).strip()
            if text:
                items.append(("goal", float(g.get("priority", 0.5)), text))
    except Exception:
        pass
    try:
        tasks = request("GET", "/api/tasks")
        for t in tasks.get("tasks", []) if isinstance(tasks, dict) else []:
            if t.get("status") in {"PENDING", "FAILED", "RUNNING"}:
                items.append(("task", 0.95 if t.get("status") == "FAILED" else 0.8, str(t.get("title", "")).strip()))
    except Exception:
        pass
    plan = STATE / "future_evolution_plan.json"
    if plan.exists():
        try:
            data = json.loads(plan.read_text(encoding="utf-8"))
            for p in data.get("predictions", [])[:10]:
                text = str(p.get("prediction", "")).strip()
                if text:
                    risk = 1.0 if p.get("risk") == "high" else 0.6
                    items.append(("prediction", risk, "استبق التطور المتوقع: " + text))
        except Exception:
            pass
    items.append(("health", 0.7, "افحص Brain بحثاً عن فشل أو نقص أو خطوة آمنة تمنع المشكلة التالية."))
    return sorted(items, key=lambda x: x[1], reverse=True)

def choose_goal():
    seen = recent_fingerprints()
    for kind, priority, text in candidates():
        fingerprint = f"{kind}:{text}"
        if fingerprint not in seen:
            return kind, priority, text, fingerprint
    kind, priority, text = candidates()[0]
    return kind, priority, text, f"{kind}:{text}"

def think_and_act(goal):
    query = urllib.parse.urlencode({"goal": goal})
    return request("POST", "/api/run?" + query)

def enqueue_self_test():
    if not CONTROL:
        return {"ok": False, "status": "CONTROL_KEY_MISSING"}
    return request("POST", "/api/device/enqueue",
                   {"X-Brain-Control-Key": CONTROL},
                   {"task": "brain_self_test", "params": {"source": "continuous_supervisor"}})

def main():
    print("JET_BRAIN_SUPERVISOR started mode=CONTINUOUS_EVOLUTION", flush=True)
    cycle = 0
    consecutive_failures = 0
    while True:
        try:
            cycle += 1
            kind, priority, goal, fingerprint = choose_goal()
            print(f"JET_BRAIN_CYCLE {cycle} SELECT kind={kind} priority={priority} goal={goal[:180]}", flush=True)
            record({"cycle": cycle, "event": "selected", "kind": kind, "goal": goal, "fingerprint": fingerprint})

            result = think_and_act(goal)
            verification = result.get("verification", {}) if isinstance(result, dict) else {}
            verified = verification.get("status") == "VERIFIED" or bool(verification.get("result_verified"))
            record({
                "cycle": cycle, "event": "completed", "goal": goal,
                "fingerprint": fingerprint, "verified": verified,
                "status": verification.get("status", result.get("status", "UNKNOWN")),
            })
            print(f"JET_BRAIN_CYCLE {cycle} VERIFY={verification.get('status', 'UNKNOWN')}", flush=True)

            status = request("GET", "/api/device/status")
            if int(status.get("queued", 0)) == 0 and int(status.get("pending", 0)) == 0:
                test = enqueue_self_test()
                print(f"JET_BRAIN_CYCLE {cycle} SELF_TEST={test.get('status', test.get('ok'))}", flush=True)

            consecutive_failures = 0 if verified else consecutive_failures + 1
            delay = min(INTERVAL * (2 ** min(consecutive_failures, 3)), 900)
            print(f"JET_BRAIN_CYCLE {cycle} NEXT_IN={delay}s", flush=True)
            time.sleep(delay)
        except KeyboardInterrupt:
            print("JET_BRAIN_SUPERVISOR stopped=INTERRUPTED", flush=True)
            return
        except Exception as exc:
            consecutive_failures += 1
            delay = min(INTERVAL * (2 ** min(consecutive_failures, 3)), 900)
            record({"cycle": cycle, "event": "error", "error": str(exc)[:500]})
            print(f"JET_BRAIN_SUPERVISOR error={str(exc)[:300]} retry_in={delay}s", flush=True)
            time.sleep(delay)

if __name__ == "__main__":
    main()
