#!/usr/bin/env python3
"""Continuous Brain supervisor: think -> act -> verify -> learn -> repeat.

The loop is intentionally evidence-first. It never grants permissions, performs
financial transactions, publishes externally, or writes code by itself.
"""
from __future__ import annotations
import json, os, time, urllib.parse, urllib.request

BASE = os.environ.get("V12_BRAIN_URL", "http://127.0.0.1:8012").rstrip("/")
CONTROL = os.environ.get("BRAIN_CONTROL_KEY", "")
INTERVAL = max(15, int(os.environ.get("BRAIN_SUPERVISOR_INTERVAL", "60")))
GOAL = os.environ.get(
    "BRAIN_AUTONOMOUS_GOAL",
    "افحص حالة Brain الحالية، حدد أهم خطوة آمنة تالية، نفذها، تحقق منها، وسجل ما تعلمته."
)

def request(method, path, headers=None, payload=None):
    data = None
    h = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def think_and_act():
    query = urllib.parse.urlencode({"goal": GOAL})
    return request("POST", "/api/run?" + query)

def enqueue_self_test():
    if not CONTROL:
        return {"ok": False, "status": "CONTROL_KEY_MISSING"}
    return request(
        "POST",
        "/api/device/enqueue",
        {"X-Brain-Control-Key": CONTROL},
        {"task": "brain_self_test", "params": {"source": "continuous_supervisor"}},
    )

def main():
    print("JET_BRAIN_SUPERVISOR started mode=CONTINUOUS_THINK_ACT_VERIFY", flush=True)
    cycle = 0
    consecutive_failures = 0
    while True:
        try:
            cycle += 1
            print(f"JET_BRAIN_CYCLE {cycle} THINK", flush=True)
            thought = think_and_act()
            ok = bool(thought.get("ok", True))
            print(
                "JET_BRAIN_CYCLE "
                + str(cycle)
                + " RESULT="
                + str(thought.get("verification", {}).get("status", thought.get("status", "UNKNOWN"))),
                flush=True,
            )

            status = request("GET", "/api/device/status")
            queued = int(status.get("queued", 0))
            pending = int(status.get("pending", 0))
            if queued == 0 and pending == 0:
                test = enqueue_self_test()
                print(
                    f"JET_BRAIN_CYCLE {cycle} SELF_TEST="
                    f"{test.get('status', test.get('ok'))}",
                    flush=True,
                )

            consecutive_failures = 0 if ok else consecutive_failures + 1
            # Back off after repeated failures, but never stop permanently.
            delay = min(INTERVAL * (2 ** min(consecutive_failures, 3)), 900)
            print(f"JET_BRAIN_CYCLE {cycle} NEXT_IN={delay}s", flush=True)
            time.sleep(delay)
        except KeyboardInterrupt:
            print("JET_BRAIN_SUPERVISOR stopped=INTERRUPTED", flush=True)
            return
        except Exception as exc:
            consecutive_failures += 1
            delay = min(INTERVAL * (2 ** min(consecutive_failures, 3)), 900)
            print(
                f"JET_BRAIN_SUPERVISOR error={str(exc)[:300]} retry_in={delay}s",
                flush=True,
            )
            time.sleep(delay)

if __name__ == "__main__":
    main()
