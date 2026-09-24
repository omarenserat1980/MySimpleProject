#!/usr/bin/env python3
"""V12 Termux agent: polls Brain V12, executes only allowlisted read-only tasks."""
import json
import os
import platform
import subprocess
import time
import urllib.parse
import urllib.request

BRAIN_URL = os.getenv("V12_BRAIN_URL", "https://electronic-brain-v12-gwwg.onrender.com").rstrip("/")
AGENT_ID = os.getenv("V12_AGENT_ID", "redmi3-01")
KEY_FILE = os.path.expanduser(os.getenv("V12_AGENT_KEY_FILE", "~/v12-agent/agent.key"))
POLL_SECONDS = max(2, int(os.getenv("V12_AGENT_POLL_SECONDS", "5")))

def load_key():
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        key = f.read().strip()
    if not key:
        raise RuntimeError("V12_AGENT_KEY_FILE is empty")
    return key

def request_json(method, path, key, payload=None):
    url = BRAIN_URL + path
    data = None
    headers = {
        "Accept": "application/json",
        "X-V12-Agent-Key": key,
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def execute(task):
    if task == "status":
        return {
            "device": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "agent": "V12-Termux-Agent",
            "status": "READY",
        }
    if task == "python_version":
        p = subprocess.run(
            ["python", "--version"],
            capture_output=True, text=True, timeout=10
        )
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    if task == "termux_path":
        p = subprocess.run(
            ["pwd"],
            capture_output=True, text=True, timeout=10
        )
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    if task == "platform":
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        }
    raise ValueError("TASK_NOT_ALLOWED")

def main():
    key = load_key()
    print(f"V12 Termux Agent connected to {BRAIN_URL}")
    print(f"Agent ID: {AGENT_ID}")
    while True:
        try:
            q = urllib.parse.urlencode({"agent_id": AGENT_ID})
            response = request_json("GET", "/api/device/poll?" + q, key)
            task = response.get("task")
            if task:
                task_id = task["task_id"]
                name = task["task"]
                try:
                    result = execute(name)
                    report = {
                        "task_id": task_id,
                        "agent_id": AGENT_ID,
                        "ok": True,
                        "result": result,
                        "error": "",
                    }
                except Exception as exc:
                    report = {
                        "task_id": task_id,
                        "agent_id": AGENT_ID,
                        "ok": False,
                        "result": {},
                        "error": str(exc)[:1000],
                    }
                out = request_json("POST", "/api/device/report", key, report)
                print(json.dumps({"task": task_id, "name": name, "report": out}, ensure_ascii=False))
            else:
                print("IDLE", flush=True)
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("V12 Termux Agent stopped.")
            return
        except Exception as exc:
            print(f"connection/error: {exc}", flush=True)
            time.sleep(max(POLL_SECONDS, 5))

if __name__ == "__main__":
    main()
