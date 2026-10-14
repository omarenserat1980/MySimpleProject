"""Opt-in Termux launcher for an installed SHA-256d Stratum miner.

This wrapper does not implement a miner. It supervises an explicitly installed
cpuminer-compatible binary on a user-owned Termux device with strict runtime,
thread, and thermal limits. Pool acceptance and revenue require separate proof.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Sequence
from urllib.parse import urlsplit

MAX_RUNTIME_SECONDS = 300
MAX_THREADS = 2
DEFAULT_RUNTIME_SECONDS = 60
DEFAULT_THREADS = 1
DEFAULT_MAX_TEMPERATURE_C = 70.0


def _positive_int(value: str | None, name: str, default: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"{name} must be an integer")
    parsed = int(value)
    if parsed < 1 or parsed > maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}")
    return parsed


def validate_pool_url(pool_url: str) -> str:
    parsed = urlsplit(pool_url)
    if parsed.scheme not in {"stratum+tcp", "stratum+ssl"}:
        raise ValueError("pool URL scheme must be stratum+tcp or stratum+ssl")
    if not parsed.hostname or parsed.port is None:
        raise ValueError("pool URL must include hostname and port")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("pool URL must not contain credentials, query, or fragment")
    if any(ch.isspace() for ch in pool_url):
        raise ValueError("pool URL must not contain whitespace")
    return pool_url


def build_command(binary: str, pool_url: str, worker: str, threads: int) -> list[str]:
    validate_pool_url(pool_url)
    if not worker or not re.fullmatch(r"[A-Za-z0-9._:@/-]{1,160}", worker):
        raise ValueError("worker must be a non-empty pool username using safe characters")
    if threads < 1 or threads > MAX_THREADS:
        raise ValueError(f"threads must be between 1 and {MAX_THREADS}")
    # cpuminer-compatible CLI. Use the conventional non-secret pool password "x";
    # do not pass wallet private keys or account passwords to a process argument.
    return [binary, "-a", "sha256d", "-o", pool_url, "-u", worker, "-p", "x", "-t", str(threads)]


def read_max_temperature_c() -> float | None:
    """Return the hottest readable Android thermal-zone value, or None if unavailable."""
    readings: list[float] = []
    for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            raw = path.read_text(encoding="ascii").strip()
            value = float(raw)
            # Linux thermal sysfs commonly reports millidegrees Celsius.
            celsius = value / 1000.0 if value > 1000 else value
            if 0 <= celsius <= 150:
                readings.append(celsius)
        except (OSError, ValueError):
            continue
    return max(readings) if readings else None


def emit(status: str, **fields: object) -> None:
    print(json.dumps({"component": "termux-bitcoin-sha256d-worker", "status": status, **fields},
                     sort_keys=True), flush=True)


def main() -> int:
    if os.environ.get("BRAIN_ENABLE_LIVE_MINING") != "YES":
        emit("BLOCKED_OPT_IN_REQUIRED",
             required="BRAIN_ENABLE_LIVE_MINING=YES",
             note="No process was started.")
        return 2
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        emit("BLOCKED_CI_ENVIRONMENT", note="Live mining is forbidden in CI.")
        return 2
    if not (os.environ.get("TERMUX_VERSION") or Path("/data/data/com.termux/files/usr").is_dir()):
        emit("BLOCKED_NOT_TERMUX", note="Run this worker on the actual user-owned Termux device.")
        return 2

    pool_url = os.environ.get("BRAIN_MINING_POOL_URL", "")
    worker = os.environ.get("BRAIN_MINING_WORKER", "")
    if not pool_url or not worker:
        emit("BLOCKED_CONFIGURATION_REQUIRED",
             required_env=["BRAIN_MINING_POOL_URL", "BRAIN_MINING_WORKER"])
        return 2
    try:
        validate_pool_url(pool_url)
        threads = _positive_int(os.environ.get("BRAIN_MINING_THREADS"), "BRAIN_MINING_THREADS",
                                DEFAULT_THREADS, MAX_THREADS)
        duration = _positive_int(os.environ.get("BRAIN_MINING_DURATION_SECONDS"),
                                 "BRAIN_MINING_DURATION_SECONDS", DEFAULT_RUNTIME_SECONDS,
                                 MAX_RUNTIME_SECONDS)
        max_temp = float(os.environ.get("BRAIN_MINING_MAX_TEMP_C", str(DEFAULT_MAX_TEMPERATURE_C)))
        if not 45.0 <= max_temp <= 80.0:
            raise ValueError("BRAIN_MINING_MAX_TEMP_C must be between 45 and 80")
        binary = os.environ.get("BRAIN_CPUMINER_BIN") or shutil.which("cpuminer")
        if not binary:
            emit("BLOCKED_MINER_NOT_INSTALLED",
                 required="Install and verify a trusted cpuminer-compatible binary first.")
            return 2
        command = build_command(binary, pool_url, worker, threads)
    except (ValueError, OSError) as exc:
        emit("BLOCKED_INVALID_CONFIGURATION", reason=str(exc))
        return 2

    initial_temp = read_max_temperature_c()
    if initial_temp is not None and initial_temp >= max_temp:
        emit("BLOCKED_THERMAL_LIMIT", temperature_c=round(initial_temp, 2),
             max_temperature_c=max_temp)
        return 2

    started = time.monotonic()
    proc: subprocess.Popen[bytes] | None = None
    stop_reason = "duration_limit"
    try:
        proc = subprocess.Popen(command)
        emit("PROCESS_STARTED_NOT_POOL_VERIFIED",
             algorithm="SHA-256d", threads=threads, runtime_limit_seconds=duration,
             initial_temperature_c=round(initial_temp, 2) if initial_temp is not None else None,
             thermal_sensor_available=initial_temp is not None,
             note="Process start alone does not prove pool authorization, accepted shares, or revenue.")
        while proc.poll() is None and time.monotonic() - started < duration:
            time.sleep(2)
            temp = read_max_temperature_c()
            if temp is not None and temp >= max_temp:
                stop_reason = "thermal_limit"
                proc.terminate()
                break
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        exit_code = proc.wait()
    except KeyboardInterrupt:
        stop_reason = "user_interrupt"
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            exit_code = proc.wait()
        else:
            exit_code = 130
    finally:
        elapsed = round(time.monotonic() - started, 2)

    final_temp = read_max_temperature_c()
    emit("WORKER_EXITED_REQUIRES_POOL_EVIDENCE",
         exit_code=exit_code, stop_reason=stop_reason, elapsed_seconds=elapsed,
         final_temperature_c=round(final_temp, 2) if final_temp is not None else None,
         pool_shares_verified=False, revenue_verified=False,
         next_evidence=["pool authorization result", "fresh measured hashrate",
                        "accepted/rejected/stale share counters", "independent payout proof"])
    return 0 if exit_code == 0 and stop_reason == "duration_limit" else 1


if __name__ == "__main__":
    raise SystemExit(main())
