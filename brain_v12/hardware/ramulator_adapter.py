"""Bounded adapter for Ramulator 2.1's Python-script interface.

The upstream 2.1 guide demonstrates running a Python example/configuration
(e.g. examples/example_config.py), not a guaranteed `ramulator2 --version`
CLI. This adapter therefore accepts a trusted local Python script. Treat that
script as executable code: run only reviewed scripts in an isolated runner.
Outputs are simulation evidence, never physical RAM telemetry.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300
MAX_SCRIPT_BYTES = 1_048_576


def _timeout(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("timeout_seconds must be an integer")
    if not 1 <= value <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")


def probe(python_executable: str = "python3") -> dict[str, Any]:
    """Check whether the Python interpreter can import Ramulator and report its version."""
    resolved = shutil.which(python_executable)
    if not resolved:
        return {
            "component": "ramulator2-memory",
            "status": "NOT_CONFIGURED",
            "available": False,
            "evidence_class": "TOOL_DISCOVERY",
            "physical_hardware_verified": False,
        }
    code = (
        "import importlib.metadata as m, json; "
        "print(json.dumps({'package':'ramulator','version':m.version('ramulator')}))"
    )
    try:
        result = subprocess.run(
            [resolved, "-c", code],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
            env={"PATH": os.path.dirname(resolved), "LANG": "C", "LC_ALL": "C"},
        )
        return {
            "component": "ramulator2-memory",
            "status": "TOOL_DISCOVERED" if result.returncode == 0 else "NOT_CONFIGURED",
            "available": result.returncode == 0,
            "python_executable": resolved,
            "return_code": result.returncode,
            "version_output": (result.stdout + result.stderr)[-2000:].strip(),
            "evidence_class": "TOOL_DISCOVERY",
            "physical_hardware_verified": False,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "component": "ramulator2-memory",
            "status": "PROBE_FAILED",
            "available": False,
            "error_type": type(exc).__name__,
            "evidence_class": "TOOL_DISCOVERY",
            "physical_hardware_verified": False,
        }


def run_script(
    script_path: str,
    *,
    python_executable: str = "python3",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run a reviewed local Ramulator Python example with a bounded timeout."""
    _timeout(timeout_seconds)
    resolved_python = shutil.which(python_executable)
    if not resolved_python:
        return {
            "component": "ramulator2-memory",
            "status": "NOT_CONFIGURED",
            "evidence_class": "SIMULATED",
            "physical_hardware_verified": False,
        }

    path = Path(script_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix != ".py" or path.stat().st_size > MAX_SCRIPT_BYTES:
        raise ValueError("script must be a regular .py file no larger than 1 MiB")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    started = time.monotonic()
    try:
        result = subprocess.run(
            [resolved_python, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            env={"PATH": os.path.dirname(resolved_python), "LANG": "C", "LC_ALL": "C"},
            cwd=str(path.parent),
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "component": "ramulator2-memory",
            "status": "TIMEOUT",
            "script_sha256": digest,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout_tail": str(exc.stdout or "")[-2000:],
            "stderr_tail": str(exc.stderr or "")[-2000:],
            "evidence_class": "SIMULATED",
            "physical_hardware_verified": False,
        }
    except OSError as exc:
        return {
            "component": "ramulator2-memory",
            "status": "EXECUTION_ERROR",
            "script_sha256": digest,
            "error_type": type(exc).__name__,
            "evidence_class": "SIMULATED",
            "physical_hardware_verified": False,
        }

    return {
        "component": "ramulator2-memory",
        "status": "SIMULATION_COMPLETED" if result.returncode == 0 else "SIMULATION_FAILED",
        "return_code": result.returncode,
        "script_sha256": digest,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
        "evidence_class": "SIMULATED",
        "physical_hardware_verified": False,
    }


def evidence_json(result: dict[str, Any]) -> str:
    """Serialize adapter evidence deterministically for artifact storage."""
    return json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
