#!/usr/bin/env python3
"""Local supervisor: queue, observe and verify Brain Emulator self-tests."""
from __future__ import annotations
import json, os, time, urllib.request

BASE = os.environ.get("V12_BRAIN_URL", "http://127.0.0.1:8012").rstrip("/")
CONTROL = os.environ.get("BRAIN_CONTROL_KEY", "")
INTERVAL = max(15, int(os.environ.get("BRAIN_SUPERVISOR_INTERVAL", "60")))

def request(method, path, headers=None, payload=None):
    data = None
    h = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def enqueue():
    if not CONTROL:
        return {"ok": False, "status": "CONTROL_KEY_MISSING"}
    return request("POST", "/api/device/enqueue",
                   {"X-Brain-Control-Key": CONTROL},
                   {"task": "brain_self_test", "params": {"source": "runtime_supervisor"}})

def main():
    print("JET_BRAIN_SUPERVISOR started", flush=True)
    last_queued = 0.0
    while True:
        try:
            status = request("GET", "/api/device/status")
            queued = int(status.get("queued", 0))
            pending = int(status.get("pending", 0))
            if queued == 0 and pending == 0 and time.time() - last_queued >= INTERVAL:
                result = enqueue()
                last_queued = time.time()
                print("JET_BRAIN_SUPERVISOR enqueue=" +
                      str(result.get("status", result.get("ok"))), flush=True)
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            return
        except Exception as exc:
            print("JET_BRAIN_SUPERVISOR error=" + str(exc)[:240], flush=True)
            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
