import json
import os
import platform
import subprocess
import time
import urllib.request

BRAIN_URL = os.getenv("V12_BRAIN_URL", "https://electronic-brain-v12-gwwg.onrender.com").rstrip("/")
AGENT_ID = os.getenv("V12_AGENT_ID", "redmi3-01")
KEY_FILE = os.path.expanduser(os.getenv("V12_AGENT_KEY_FILE", "~/v12-agent/agent.key"))
POLL_SECONDS = int(os.getenv("V12_POLL_SECONDS", "5"))
TIMEOUT = 15

ALLOWED_TASKS = {"status", "python_version", "termux_path", "platform"}

def load_key():
    with open(KEY_FILE, "r", encoding="utf-8") as f:
        key = f.read().strip()
    if not key:
        raise RuntimeError("V12_AGENT_KEY is empty")
    return key

def request(method, path, key, payload=None):
    data = None
    headers = {"X-V12-Agent-Key": key, "User-Agent": "V12-Termux-Agent/1.0"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BRAIN_URL + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))

def execute(task, params):
    if task == "status":
        return {
            "device": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "agent": "V12-Termux-Agent",
            "status": "READY",
        }
    if task == "python_version":
        p = subprocess.run(["python", "--version"], capture_output=True, text=True, timeout=10)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    if task == "termux_path":
        p = subprocess.run(["pwd"], capture_output=True, text=True, timeout=10)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    if task == "platform":
        return {"system": platform.system(), "release": platform.release(), "machine": platform.machine()}
    raise ValueError("TASK_NOT_ALLOWED")

def main():
    key = load_key()
    print(f"V12 Termux Agent connected to {BRAIN_URL}")
    print(f"Agent ID: {AGENT_ID}")
    while True:
        try:
            r = request("GET", "/api/device/poll?agent_id=" + urllib.parse.quote(AGENT_ID), key)
            task = r.get("task")
            if task:
                task_id = task["task_id"]
                name = task["task"]
                try:
                    result = execute(name, task.get("params") or {})
                    report = {"task_id": task_id, "agent_id": AGENT_ID, "ok": True, "result": result, "error": ""}
                except Exception as exc:
                    report = {"task_id": task_id, "agent_id": AGENT_ID, "ok": False, "result": {}, "error": str(exc)[:1000]}
                print("TASK", task_id, name)
                print(request("POST", "/api/device/report", key, report))
            else:
                print(".", end="", flush=True)
        except Exception as exc:
            print("\nconnection:", str(exc)[:200])
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    import urllib.parse
    main()
