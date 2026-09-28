"""Deterministic repository verification for Electronic Brain CI.

The verifier always writes verification/latest.json, even when one or more
checks fail, and executes every check so a single failure does not hide later
failures.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "verification" / "latest.json"

COMMANDS: list[tuple[str, list[str]]] = [
    ("compile_v7", [sys.executable, "-m", "compileall", "-q", "brain_v7/braincore_v2"]),
    ("compile_v12", [sys.executable, "-m", "compileall", "-q", "brain_v12"]),
    (
        "speed_tests",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "brain_v7/braincore_v2/test_speed_pipeline.py",
            "brain_v7/braincore_v2/test_speed_optimizer.py",
            "brain_v7/braincore_v2/test_benchmark_router.py",
            "brain_v7/braincore_v2/test_production_speed_optimizer.py",
            "brain_v7/braincore_v2/test_throughput_metrics.py",
            "brain_v7/braincore_v2/test_adaptive_concurrency.py",
        ],
    ),
    (
        "cinema_v6_tests",
        [sys.executable, "-m", "pytest", "-q", "brain_v7/braincore_v2/test_cinema_engine_v6.py"],
    ),
    (
        "brain_v12_tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "brain_v12/tests", "-v"],
    ),
]


def run_command(name: str, command: list[str]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=12 * 60,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
        )
        result: dict[str, Any] = {
            "name": name,
            "command": command,
            "returncode": proc.returncode,
            "duration_s": round(time.monotonic() - started, 3),
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "name": name,
            "command": command,
            "returncode": 124,
            "duration_s": round(time.monotonic() - started, 3),
            "stdout_tail": str(exc.stdout or "")[-4000:],
            "stderr_tail": ("timeout after 12 minutes\n" + str(exc.stderr or ""))[-4000:],
        }
    except OSError as exc:
        result = {
            "name": name,
            "command": command,
            "returncode": 127,
            "duration_s": round(time.monotonic() - started, 3),
            "stdout_tail": "",
            "stderr_tail": f"unable to start command: {exc}",
        }
    result["status"] = "PASS" if result["returncode"] == 0 else "FAIL"
    return result


def main() -> int:
    started_at = time.time()
    results = [run_command(name, command) for name, command in COMMANDS]
    failed = [item["name"] for item in results if item["status"] != "PASS"]

    report = {
        "version": 2,
        "status": "PASS" if not failed else "FAIL",
        "failed_checks": failed,
        "python": sys.version,
        "platform": sys.platform,
        "started_at": started_at,
        "completed_at": time.time(),
        "results": results,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
