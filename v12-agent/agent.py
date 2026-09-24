#!/usr/bin/env python3
"""V12 Termux Agent: authenticated polling bridge with an allowlisted local task runner."""
import json
import os
import platform
import time
import urllib.request
import urllib.error
import urllib.parse

BRAIN_URL = os.getenv("V12_BRAIN_URL", "https://electronic-brain-v12-gwwg.onrender.com").rstrip("/")
AGENT_ID = os.getenv("V12_AGENT_ID", "redmi3-01")
KEY_FILE = os.path.expanduser(os.getenv("V12_AGENT_KEY_FILE", "~/v12-agent/agent.key"))
POLL_SECONDS = float(os.getenv("V12_POLL_SECONDS", "3"))

def read_key():
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        key = f.read().strip()
    if not key:
        raise RuntimeError("V12_AGENT_KEY_FILE is empty")
    return key

def request(method, path, payload=None, key=None, timeout=20):
    data = None
    headers = {"Accept": "application/json", "User-Agent": "V12-Termux-Agent/1.0"}
    if key:
        headers["X-V12-Agent-Key"] = key
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BRAIN_URL + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def execute(task, params):
    if task == "status":
        return {"device": platform.system(), "machine": platform.machine(),
                "python": platform.python_version(), "agent": "V12-Termux-Agent",
                "agent_id": AGENT_ID, "status": "READY"}
    if task == "python_version":
        return {"python": platform.python_version()}
    if task == "termux_path":
        return {"path": os.getcwd(), "home": os.path.expanduser("~")}
    if task == "platform":
        return {"system": platform.system(), "release": platform.release(),
                "machine": platform.machine(), "processor": platform.processor()}
    raise ValueError("task_not_allowed")

def main():
    key = read_key()
    print("V12-Termux-Agent ONLINE")
    print("Brain:", BRAIN_URL)
    print("Agent:", AGENT_ID)
    while True:
        try:
            polled = request("GET", "/api/device/poll?agent_id=" + urllib.parse.quote(AGENT_ID, safe=""), key=key)
            task = polled.get("task")
            if task:
                task_id = task["task_id"]
                name = task.get("task", "")
                print("TASK", task_id, name)
                try:
                    result = execute(name, task.get("params") or {})
                    report = {"task_id": task_id, "agent_id": AGENT_ID,
                              "ok": True, "result": result, "error": ""}
                except Exception as exc:
                    report = {"task_id": task_id, "agent_id": AGENT_ID,
                              "ok": False, "result": {}, "error": str(exc)[:1000]}
                print("REPORT", request("POST", "/api/device/report", report, key=key))
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("V12-Termux-Agent STOPPED")
            return
        except Exception as exc:
            print("POLL_ERROR:", str(exc)[:300])
            time.sleep(max(POLL_SECONDS, 5))

if __name__ == "__main__":
    import urllib.parse
    main()
