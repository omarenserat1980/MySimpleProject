"""Opt-in Termux launcher for an installed SHA-256d Stratum miner.

This supervises a locally installed cpuminer-compatible binary. It does not
implement hashing. Pool output is parsed as evidence candidates, not independently
authenticated proof; payout/revenue remains a separate gate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
from urllib.parse import urlsplit

MAX_RUNTIME_SECONDS = 300
MAX_THREADS = 2
DEFAULT_RUNTIME_SECONDS = 60
DEFAULT_THREADS = 1
DEFAULT_MAX_TEMPERATURE_C = 70.0

# Common cpuminer-family output formats; unmatched lines are never emitted raw.
ACCEPTED_RE = re.compile(r"\baccepted\b", re.IGNORECASE)
REJECTED_RE = re.compile(r"\brejected\b|\bstale\b", re.IGNORECASE)
HASHRATE_RE = re.compile(r"(?P<rate>[0-9]+(?:\.[0-9]+)?)\s*(?P<unit>[kMGT]?hash/s|[kMGT]H/s)", re.IGNORECASE)
AUTH_RE = re.compile(r"\b(authori[sz]ed|authorized|authorization successful|stratum subscribed)\b", re.IGNORECASE)


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
    return [binary, "-a", "sha256d", "-o", pool_url, "-u", worker, "-p", "x", "-t", str(threads)]


def parse_miner_line(line: str, counters: dict[str, object]) -> None:
    """Accumulate conservative counters from known miner output; never trust line alone as payout proof."""
    if ACCEPTED_RE.search(line):
        counters["accepted_shares"] = int(counters["accepted_shares"]) + 1
    if REJECTED_RE.search(line):
        counters["rejected_or_stale_lines"] = int(counters["rejected_or_stale_lines"]) + 1
    if AUTH_RE.search(line):
        counters["authorization_message_seen"] = True
    matches = list(HASHRATE_RE.finditer(line))
    if matches:
        match = matches[-1]
        rate = float(match.group("rate"))
        unit = match.group("unit").lower()
        scale = 1.0
        if unit.startswith("k"):
            scale = 1e3
        elif unit.startswith("m"):
            scale = 1e6
        elif unit.startswith("g"):
            scale = 1e9
        elif unit.startswith("t"):
            scale = 1e12
        counters["last_reported_hashrate_hs"] = rate * scale
        counters["hashrate_unit_source"] = "miner_stdout_stderr_unverified"


def read_max_temperature_c() -> float | None:
    readings: list[float] = []
    for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            value = float(path.read_text(encoding="ascii").strip())
            celsius = value / 1000.0 if value > 1000 else value
            if 0 <= celsius <= 150:
                readings.append(celsius)
        except (OSError, ValueError):
            continue
    return max(readings) if readings else None


def supervisor_exit_code(stop_reason: str, miner_exit_code: int) -> int:
    """Return the supervisor result separately from the miner process exit code."""
    if stop_reason == "duration_limit":
        # SIGTERM is expected when the supervisor enforces its configured time cap.
        return 0
    if stop_reason == "user_interrupt":
        return 130
    return 1


def emit(status: str, **fields: object) -> None:
    print(json.dumps({"component": "termux-bitcoin-sha256d-worker", "status": status, **fields},
                     sort_keys=True), flush=True)


def _read_output(stream, counters: dict[str, object], lock: threading.Lock) -> None:
    try:
        for raw_line in iter(stream.readline, b""):
            line = raw_line.decode("utf-8", errors="replace").strip()
            with lock:
                parse_miner_line(line, counters)
    finally:
        stream.close()


def main() -> int:
    if os.environ.get("BRAIN_ENABLE_LIVE_MINING") != "YES":
        emit("BLOCKED_OPT_IN_REQUIRED", required="BRAIN_ENABLE_LIVE_MINING=YES", note="No process was started.")
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
        emit("BLOCKED_CONFIGURATION_REQUIRED", required_env=["BRAIN_MINING_POOL_URL", "BRAIN_MINING_WORKER"])
        return 2
    try:
        validate_pool_url(pool_url)
        threads = _positive_int(os.environ.get("BRAIN_MINING_THREADS"), "BRAIN_MINING_THREADS", DEFAULT_THREADS, MAX_THREADS)
        duration = _positive_int(os.environ.get("BRAIN_MINING_DURATION_SECONDS"), "BRAIN_MINING_DURATION_SECONDS", DEFAULT_RUNTIME_SECONDS, MAX_RUNTIME_SECONDS)
        max_temp = float(os.environ.get("BRAIN_MINING_MAX_TEMP_C", str(DEFAULT_MAX_TEMPERATURE_C)))
        if not 45.0 <= max_temp <= 80.0:
            raise ValueError("BRAIN_MINING_MAX_TEMP_C must be between 45 and 80")
        binary = os.environ.get("BRAIN_CPUMINER_BIN") or shutil.which("cpuminer")
        if not binary:
            emit("BLOCKED_MINER_NOT_INSTALLED", required="Install and verify a trusted cpuminer-compatible binary first.")
            return 2
        command = build_command(binary, pool_url, worker, threads)
    except (ValueError, OSError) as exc:
        emit("BLOCKED_INVALID_CONFIGURATION", reason=str(exc))
        return 2

    initial_temp = read_max_temperature_c()
    if initial_temp is not None and initial_temp >= max_temp:
        emit("BLOCKED_THERMAL_LIMIT", temperature_c=round(initial_temp, 2), max_temperature_c=max_temp)
        return 2

    counters: dict[str, object] = {
        "accepted_shares": 0,
        "rejected_or_stale_lines": 0,
        "authorization_message_seen": False,
        "last_reported_hashrate_hs": None,
        "hashrate_unit_source": None,
    }
    lock = threading.Lock()
    started = time.monotonic()
    proc = None
    stop_reason = "duration_limit"
    exit_code = 1
    reader = None
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        reader = threading.Thread(target=_read_output, args=(proc.stdout, counters, lock), daemon=True)
        reader.start()
        emit("PROCESS_STARTED_NOT_POOL_VERIFIED", algorithm="SHA-256d", threads=threads,
             runtime_limit_seconds=duration,
             initial_temperature_c=round(initial_temp, 2) if initial_temp is not None else None,
             thermal_sensor_available=initial_temp is not None,
             note="Miner output is parsed as a candidate signal; process start is not pool proof.")
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
        if reader is not None:
            reader.join(timeout=2)
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
    except OSError as exc:
        emit("BLOCKED_PROCESS_LAUNCH_FAILED", reason=type(exc).__name__)
        return 2
    finally:
        elapsed = round(time.monotonic() - started, 2)

    final_temp = read_max_temperature_c()
    with lock:
        evidence = dict(counters)
    pool_signal = bool(evidence["authorization_message_seen"] or int(evidence["accepted_shares"]) > 0)
    emit("WORKER_EXITED_REQUIRES_POOL_EVIDENCE",
         exit_code=exit_code, stop_reason=stop_reason, elapsed_seconds=elapsed,
         final_temperature_c=round(final_temp, 2) if final_temp is not None else None,
         miner_output_counters=evidence,
         pool_signal_seen_in_miner_output=pool_signal,
         pool_connection_verified=False,
         accepted_shares_verified=False,
         revenue_verified=False,
         next_evidence=["independent pool-side authorization/session", "pool-side measured hashrate",
                        "pool-side accepted/rejected/stale share counters", "independent payout proof"])
    return supervisor_exit_code(stop_reason, exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
