"""Repository-level verification runner for Electronic Brain.

Produces a machine-readable report so CI state remains inspectable even when a
GitHub Checks/Actions connector does not expose workflow runs.
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

COMMANDS = [
    ("compile_v7", [sys.executable, "-m", "compileall", "-q", "brain_v7/braincore_v2"]),
    ("compile_v12", [sys.executable, "-m", "compileall", "-q", "brain_v12"]),
    ("speed_tests", [sys.executable, "-m", "pytest", "-q",
                     "brain_v7/braincore_v2/test_speed_pipeline.py",
                     "brain_v7/braincore_v2/test_speed_optimizer.py",
                     "brain_v7/braincore_v2/test_benchmark_router.py",
                     "brain_v7/braincore_v2/test_production_speed_optimizer.py"]),
    ("cinema_v6_tests", [sys.executable, "-m", "pytest", "-q",
                         "brain_v7/braincore_v2/test_cinema_engine_v6.py"]),
    ("brain_v12_tests", [sys.executable, "-m", "unittest", "discover",
                         "-s", "brain_v12/tests", "-v"]),
]

def main() -> int:
    report = {"version": 1, "started_at": time.time(), "results": [], "status": "PASS"}
    for name, command in COMMANDS:
        started = time.monotonic()
        proc = subprocess.run(command, text=True, capture_output=True)
        item = {
            "name": name,
            "returncode": proc.returncode,
            "duration_s": round(time.monotonic() - started, 3),
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
        report["results"].append(item)
        if proc.returncode != 0:
            report["status"] = "FAIL"
            break
    report["completed_at"] = time.time()
    out = Path("verification/latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
