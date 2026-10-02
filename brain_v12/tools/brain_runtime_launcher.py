from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state" / "runtime.json"


def detect_python() -> str | None:
    candidates = [
        os.getenv("BRAIN_PYTHON_EXECUTABLE"),
        os.getenv("V12_PYTHON_EXECUTABLE"),
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for item in candidates:
        if item and os.path.isfile(item) and os.access(item, os.X_OK):
            return item
    return None


def main() -> int:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    python = detect_python()
    if not python:
        STATE.write_text(json.dumps({
            "status": "WAITING_FOR_RUNTIME",
            "reason": "PYTHON_NOT_FOUND",
            "root": str(ROOT),
        }, ensure_ascii=False) + "\n", encoding="utf-8")
        return 42

    env = os.environ.copy()
    env["BRAIN_PYTHON_EXECUTABLE"] = python
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    STATE.write_text(json.dumps({
        "status": "READY",
        "python": python,
        "root": str(ROOT),
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    return subprocess.call(
        [python, str(ROOT / "brain_v12" / "tools" / "brain_emulator_agent.py")],
        cwd=str(ROOT),
        env=env,
    )


if __name__ == "__main__":
    raise SystemExit(main())
