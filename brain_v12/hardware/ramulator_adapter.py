"""Fail-closed adapter for an externally installed Ramulator 2.x executable.

This module does not install software or download upstream code. It only runs a
locally configured executable with a caller-supplied configuration file. All
reported memory results are simulation evidence, never physical RAM telemetry.
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
MAX_CONFIG_BYTES = 1_048_576


def probe(executable: str = "ramulator2") -> dict[str, Any]:
    """Report whether Ramulator is installed and expose its version output."""
    resolved = shutil.which(executable)
    if not resolved:
        return {
            "component": "ramulator2-memory",
            "status": "NOT_CONFIGURED",
            "available": False,
            "evidence_class": "TOOL_DISCOVERY",
            "physical_hardware_verified": False,
        }
    try:
        result = subprocess.run(
            [resolved, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            shell=False,
        )
        return {
            "component": "ramulator2-memory",
            "status": "TOOL_DISCOVERED",
            "available": True,
            "executable": resolved,
            "version_exit_code": result.returncode,
            "version_output": (result.stdout + result.stderr)[:2000].strip(),
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


def run_config(
    config_path: str,
    *,
    executable: str = "ramulator2",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run Ramulator against a local config under a strict timeout.

    No shell is used, no dependency is installed, no network is requested, and
    stdout/stderr are truncated before returning. Callers should execute this
    adapter in a sandbox/container for stronger resource and filesystem limits.
    """
    resolved = shutil.which(executable)
    if not resolved:
        return {
            "component": "ramulator2-memory",
            "status": "NOT_CONFIGURED",
            "evidence_class": "SIMULATED",
            "physical_hardware_verified": False,
        }

    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool):
        raise ValueError("timeout_seconds must be an integer")
    if not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")

    path = Path(config_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError("config must be a regular file no larger than 1 MiB")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    started = time.monotonic()
    try:
        result = subprocess.run(
            [resolved, "-f", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            env={"PATH": os.path.dirname(resolved), "LANG": "C", "LC_ALL": "C"},
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "component": "ramulator2-memory",
            "status": "TIMEOUT",
            "config_sha256": digest,
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
            "config_sha256": digest,
            "error_type": type(exc).__name__,
            "evidence_class": "SIMULATED",
            "physical_hardware_verified": False,
        }

    return {
        "component": "ramulator2-memory",
        "status": "SIMULATION_COMPLETED" if result.returncode == 0 else "SIMULATION_FAILED",
        "return_code": result.returncode,
        "config_sha256": digest,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
        "evidence_class": "SIMULATED",
        "physical_hardware_verified": False,
    }


def evidence_json(result: dict[str, Any]) -> str:
    """Serialize adapter evidence deterministically for artifact storage."""
    return json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
