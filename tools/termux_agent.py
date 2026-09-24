#!/usr/bin/env python3
"""V12 Termux agent: outbound-only polling bridge.

This process never opens a listening port. It polls the Brain V12 HTTPS API,
executes only fixed allowlisted tasks, and posts the result back.
"""
from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BRAIN_URL = os.getenv("V12_BRAIN_URL", "https://electronic-brain-v12-gwwg.onrender.com").rstrip("/")
AGENT_ID = os.getenv("V12_AGENT_ID", "redmi3-termux-01")
KEY_FILE = Path(os.getenv("V12_AGENT_KEY_FILE", str(Path.home() / "v12-agent" / "agent.key")))
POLL_SECONDS = max(2.0, float(os.getenv("V12_POLL_SECONDS", "3")))

def load_key() -> str:
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("V12 agent key file is empty")
    return key

def request_json(method: str, path: str, key: str, payload: dict | None = None) -> dict:
    data = None
    headers = {
        "Accept": "application/json",
        "X-V12-Agent-Key": key,
        "User-Agent": "V12-Termux-Agent/1.0",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(BRAIN_URL + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=25) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)

def execute(task: str, params: dict) -> dict:
    if task == "status":
        return {
            "device": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "agent": "V12-Termux-Agent",
            "agent_id": AGENT_ID,
            "status": "READY",
        }
    if task == "python_version":
        return {"python": platform.python_version()}
    if task == "termux_path":
        return {"path": str(Path.cwd())}
    if task == "platform":
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        }
    raise ValueError("task_not_allowed")

def main() -> None:
    key = load_key()
    print("V12-Termux-Agent outbound bridge started")
    print(f"Brain: {BRAIN_URL}")
    print(f"Agent ID: {AGENT_ID}")
    print("No local listening port is opened.")
    while True:
        try:
            response = request_json("GET", f"/api/device/poll?agent_id={AGENT_ID}", key)
            task = response.get("task")
            if task:
                task_id = task.get("task_id", "")
                name = task.get("task", "")
                params = task.get("params") or {}
                try:
                    result = execute(name, params)
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
                print(json.dumps({"task": name, "report": report}, ensure_ascii=False))
                request_json("POST", "/api/device/report", key, report)
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            print(f"bridge warning: {exc}")
        except KeyboardInterrupt:
            print("V12-Termux-Agent stopped")
            return
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()
