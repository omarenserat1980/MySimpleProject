#!/usr/bin/env python3
"""Run the Brain independence gate without GitHub Actions or Windows."""
from __future__ import annotations
import json, os, platform, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "brain6_artifacts" / "independence_gate"
EVIDENCE_FILE = EVIDENCE_DIR / "independence_gate.json"
TESTS = ["tests/test_executor_pool.py"]

def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    command = [sys.executable, "-m", "pytest", "-q", *TESTS]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(command, cwd=ROOT, env=env, text=True,
                          capture_output=True)
    status = "PASS" if proc.returncode == 0 else "FAIL"
    evidence = {
        "schema": "brain.independence_gate.v1",
        "status": status,
        "verified": proc.returncode == 0,
        "gate": "BRAIN_INDEPENDENT_EXECUTOR_POOL",
        "execution_authority": "brain-local",
        "github_runner_required": False,
        "windows_required": False,
        "tests": TESTS,
        "command": command,
        "returncode": proc.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "platform": platform.platform(),
        "python": sys.version,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2, ensure_ascii=False),
                             encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return proc.returncode

if __name__ == "__main__":
    raise SystemExit(main())
