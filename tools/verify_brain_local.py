#!/usr/bin/env python3
"""Single entrypoint for proving the local Brain execution path."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "tools" / "brain_runtime_doctor.py"
GATE = ROOT / "tools" / "brain_independent_gate.py"
OUT = ROOT / "brain6_artifacts" / "independence_gate" / "brain_local_verification.json"

def run(path):
    p = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True,
                       capture_output=True)
    return {
        "script": str(path.relative_to(ROOT)),
        "returncode": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
        "status": "PASS" if p.returncode == 0 else "FAIL",
    }

def main():
    doctor = run(DOCTOR)
    if doctor["returncode"] != 0:
        result = {
            "schema": "brain.local_verification.v1",
            "status": "NOT_READY",
            "verified": False,
            "doctor": doctor,
            "gate": None,
            "github_runner_required": False,
            "windows_required": False,
        }
    else:
        gate = run(GATE)
        result = {
            "schema": "brain.local_verification.v1",
            "status": "VERIFIED" if gate["returncode"] == 0 else "FAILED",
            "verified": gate["returncode"] == 0,
            "doctor": doctor,
            "gate": gate,
            "github_runner_required": False,
            "windows_required": False,
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verified"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
