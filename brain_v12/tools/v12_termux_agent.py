"""V12 Termux Agent: poll Brain V12, execute only allowlisted local tasks, report results."""
from __future__ import annotations

import json
import os
import platform
import time
import urllib.error
import urllib.request

BRAIN_URL = os.getenv("V12_BRAIN_URL", "https://electronic-brain-v12-gwwg.onrender.com").rstrip("/")
AGENT_KEY = os.getenv("V12_AGENT_KEY", "")
AGENT_ID = os.getenv("V12_AGENT_ID", "android-termux-01")
POLL_SECONDS = max(2, int(os.getenv("V12_AGENT_POLL_SECONDS", "5")))


def request(method, path, body=None):
    data = None
    headers = {"X-V12-Agent-Key": AGENT_KEY}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BRAIN_URL + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


def execute(task):
    if task == "status":
        return {
            "device": "Android",
            "machine": platform.machine(),
            "python": platform.python_version(),
            "agent": AGENT_ID,
            "status": "READY",
        }
    if task == "python_version":
        return {"python": platform.python_version()}
    if task == "termux_path":
        return {"cwd": os.getcwd(), "home": os.path.expanduser("~")}
    if task == "platform":
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
    raise ValueError("TASK_NOT_ALLOWED")


def main():
    if not AGENT_KEY:
        raise SystemExit("V12_AGENT_KEY is required")
    print(f"V12 Termux Agent {AGENT_ID} -> {BRAIN_URL}")
    while True:
        try:
            poll = request("GET", f"/api/device/poll?agent_id={AGENT_ID}")
            task = poll.get("task")
            if task:
                task_id = task["task_id"]
                name = task["task"]
                try:
                    result = execute(name)
                    report = request("POST", "/api/device/report", {
                        "task_id": task_id,
                        "agent_id": AGENT_ID,
                        "ok": True,
                        "result": result,
                        "error": "",
                    })
                    print(json.dumps({"task": name, "report": report}, ensure_ascii=False))
                except Exception as exc:
                    report = request("POST", "/api/device/report", {
                        "task_id": task_id,
                        "agent_id": AGENT_ID,
                        "ok": False,
                        "result": {},
                        "error": str(exc),
                    })
                    print(json.dumps({"task": name, "report": report}, ensure_ascii=False))
            time.sleep(POLL_SECONDS)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            print(f"agent loop: {exc}")
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
