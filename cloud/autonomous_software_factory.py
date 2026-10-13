"""Verification cycle for the canonical Brain V12 runtime."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], timeout: int = 900) -> int:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    print(json.dumps({
        "event": "brain_v12_verification_command",
        "cmd": cmd,
        "rc": p.returncode,
        "stdout": p.stdout[-3000:],
        "stderr": p.stderr[-3000:],
    }, ensure_ascii=False), flush=True)
    return p.returncode


def cycle() -> int:
    print("BRAIN_V12_VERIFICATION_CYCLE=1", flush=True)
    checks = [
        ["python", "-m", "compileall", "-q", "brain_v12", "cloud"],
        ["python", "-m", "pytest", "-q", "brain_v12/tests"],
    ]
    for cmd in checks:
        if run(cmd):
            print("BRAIN_V12_VERIFICATION_GATE=FAIL", flush=True)
            return 1
    print("BRAIN_V12_VERIFICATION_GATE=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(cycle())
