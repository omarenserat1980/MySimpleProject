"""Bounded RTL simulator adapter; Python orchestrates tools but is not RTL.

Only allowlisted repository testbenches can be compiled. PASS requires a zero
exit code AND the exact testbench success marker. Missing tools, timeouts,
cancellation, or incomplete evidence never produce PASS.
"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any

from .sha256d_execution_contract import make_layer_result, utc_now

MAX_TIMEOUT_SECONDS = 60.0
MAX_NONCE = 0xFFFFFFFF
RTL_ROOT = Path(__file__).resolve().parents[1] / "asic" / "rtl"

CASES: dict[str, dict[str, Any]] = {
    "genesis_nonce_search": {
        "top": "tb_bitcoin_genesis_nonce_search",
        "sources": [
            "sha256_compress.sv", "sha256d_header_hash.sv",
            "bitcoin_pow_target_check.sv", "bitcoin_nonce_sweep.sv",
            "tb_bitcoin_genesis_nonce_search.sv",
        ],
        "marker": "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED",
    },
    "nonce_sweep": {
        "top": "tb_bitcoin_nonce_sweep",
        "sources": [
            "sha256_compress.sv", "sha256d_header_hash.sv",
            "bitcoin_pow_target_check.sv", "bitcoin_nonce_sweep.sv",
            "tb_bitcoin_nonce_sweep.sv",
        ],
        "marker": "ALL_NONCE_SWEEP_TESTS_PASSED",
    },
    "header_hash": {
        "top": "tb_sha256d_header_hash",
        "sources": [
            "sha256_compress.sv", "sha256d_header_hash.sv",
            "tb_sha256d_header_hash.sv",
        ],
        "marker": "ALL_SHA256D_HEADER_RTL_TESTS_PASSED",
    },
}


def validate_nonce_range(start_nonce: int, max_attempts: int) -> None:
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= MAX_NONCE:
        raise ValueError("NONCE_START_OUT_OF_UINT32_RANGE")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 1_000_000:
        raise ValueError("NONCE_ATTEMPTS_OUT_OF_RANGE")
    if start_nonce + max_attempts - 1 > MAX_NONCE:
        raise ValueError("NONCE_RANGE_WOULD_WRAP_UINT32")


def _run_command(
    command: list[str],
    *,
    timeout_seconds: float,
    cancel_event: threading.Event | None = None,
    log_path: Path,
) -> dict[str, Any]:
    """Run one tool command with bounded timeout and cooperative cancellation."""
    start = time.monotonic()
    try:
        with log_path.open("wb") as log:
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            while proc.poll() is None:
                if cancel_event is not None and cancel_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return {"status": "CANCELLED", "exit_code": proc.returncode,
                            "elapsed_seconds": round(time.monotonic() - start, 4)}
                if time.monotonic() - start >= timeout_seconds:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return {"status": "TIMEOUT", "exit_code": proc.returncode,
                            "elapsed_seconds": round(time.monotonic() - start, 4)}
                time.sleep(0.02)
            return {"status": "PASS" if proc.returncode == 0 else "FAIL",
                    "exit_code": proc.returncode,
                    "elapsed_seconds": round(time.monotonic() - start, 4)}
    except FileNotFoundError:
        return {"status": "BLOCKED", "exit_code": None, "error_code": "TOOL_NOT_FOUND",
                "elapsed_seconds": round(time.monotonic() - start, 4)}
    except OSError as exc:
        return {"status": "FAIL", "exit_code": None,
                "error_code": "TOOL_LAUNCH_ERROR_" + type(exc).__name__,
                "elapsed_seconds": round(time.monotonic() - start, 4)}


def classify_simulation_result(sim_result: dict[str, Any], output: str, required_marker: str) -> tuple[str, str | None, bool]:
    """A zero exit code without the exact success marker is not a PASS."""
    marker_found = required_marker in output
    if sim_result.get("status") != "PASS":
        return str(sim_result.get("status", "FAIL")), str(sim_result.get("error_code") or "RTL_SIMULATION_FAILED"), marker_found
    if not marker_found:
        return "FAIL", "SUCCESS_MARKER_MISSING", False
    return "PASS", None, True


def run_rtl_smoke(
    case: str = "genesis_nonce_search",
    *,
    timeout_seconds: float = 30.0,
    cancel_event: threading.Event | None = None,
    rtl_root: Path | None = None,
) -> dict[str, Any]:
    """Compile and execute a repository RTL testbench; no pool/network access."""
    started_at = utc_now()
    if case not in CASES:
        return make_layer_result(layer="rtl_simulator", status="BLOCKED",
                                 error_code="RTL_CASE_NOT_ALLOWLISTED")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0.1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        return make_layer_result(layer="rtl_simulator", status="BLOCKED",
                                 error_code="TIMEOUT_OUT_OF_RANGE")
    if cancel_event is not None and cancel_event.is_set():
        return make_layer_result(layer="rtl_simulator", status="CANCELLED",
                                 error_code="CANCELLED_BEFORE_START",
                                 started_at_utc=started_at)
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if not iverilog or not vvp:
        missing = [name for name, path in (("iverilog", iverilog), ("vvp", vvp)) if not path]
        return make_layer_result(layer="rtl_simulator", status="BLOCKED",
                                 error_code="MISSING_TOOLS:" + ",".join(missing),
                                 started_at_utc=started_at)
    root = rtl_root or RTL_ROOT
    spec = CASES[case]
    source_paths = [root / name for name in spec["sources"]]
    missing_sources = [path.name for path in source_paths if not path.is_file()]
    if missing_sources:
        return make_layer_result(layer="rtl_simulator", status="BLOCKED",
                                 error_code="MISSING_RTL_SOURCES:" + ",".join(missing_sources),
                                 started_at_utc=started_at)
    source_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
    }
    # One wall-clock budget covers both compilation and simulation, rather than
    # allowing each phase to consume the full timeout independently.
    deadline = time.monotonic() + float(timeout_seconds)
    with tempfile.TemporaryDirectory(prefix="brain-sha256d-rtl-") as tmp:
        work = Path(tmp)
        binary = work / "testbench.vvp"
        compile_log = work / "compile.log"
        sim_log = work / "simulation.log"
        compile_remaining = deadline - time.monotonic()
        if compile_remaining <= 0:
            return make_layer_result(
                layer="rtl_simulator", status="TIMEOUT", error_code="OVERALL_TIMEOUT",
                evidence={"case": case, "phase": "compile", "source_sha256": source_hashes,
                          "execution_scope": "LOCAL_RTL_SIMULATION_ONLY"},
                started_at_utc=started_at,
            )
        compile_result = _run_command(
            [iverilog, "-g2012", "-Wall", "-s", spec["top"], "-o", str(binary),
             *[str(path) for path in source_paths]],
            timeout_seconds=compile_remaining, cancel_event=cancel_event,
            log_path=compile_log,
        )
        if compile_result["status"] != "PASS":
            status = compile_result["status"]
            return make_layer_result(
                layer="rtl_simulator", status=status,
                error_code=compile_result.get("error_code", "RTL_COMPILE_" + status),
                evidence={"case": case, "phase": "compile", "tool": "iverilog",
                          "tool_result": compile_result, "source_sha256": source_hashes},
                started_at_utc=started_at,
            )
        simulation_remaining = deadline - time.monotonic()
        if simulation_remaining <= 0:
            return make_layer_result(
                layer="rtl_simulator", status="TIMEOUT", error_code="OVERALL_TIMEOUT",
                evidence={
                    "case": case,
                    "top_module": spec["top"],
                    "compiler": Path(iverilog).name,
                    "simulator": Path(vvp).name,
                    "source_sha256": source_hashes,
                    "compile": compile_result,
                    "simulation": {"status": "TIMEOUT", "exit_code": None,
                                   "error_code": "OVERALL_TIMEOUT"},
                    "required_success_marker": spec["marker"],
                    "success_marker_found": False,
                    "execution_scope": "LOCAL_RTL_SIMULATION_ONLY",
                },
                started_at_utc=started_at,
            )
        sim_result = _run_command(
            [vvp, str(binary)], timeout_seconds=simulation_remaining,
            cancel_event=cancel_event, log_path=sim_log,
        )
        output = sim_log.read_text(encoding="utf-8", errors="replace")[-12000:] if sim_log.exists() else ""
        status, error, marker_found = classify_simulation_result(sim_result, output, spec["marker"])
        evidence = {
            "case": case,
            "top_module": spec["top"],
            "compiler": Path(iverilog).name,
            "simulator": Path(vvp).name,
            "source_sha256": source_hashes,
            "compile": compile_result,
            "simulation": sim_result,
            "required_success_marker": spec["marker"],
            "success_marker_found": marker_found,
            "simulation_output_tail": output,
            "execution_scope": "LOCAL_RTL_SIMULATION_ONLY",
        }
        return make_layer_result(layer="rtl_simulator", status=status, evidence=evidence,
                                 error_code=error, started_at_utc=started_at,
                                 finished_at_utc=utc_now())


def normalize_cpu_benchmark(result: dict[str, Any]) -> dict[str, Any]:
    """Map a CPU benchmark into the same contract without implying RTL or mining."""
    digest = result.get("last_digest_hex") if isinstance(result, dict) else None
    count = result.get("hashes_completed") if isinstance(result, dict) else None
    elapsed = result.get("elapsed_seconds") if isinstance(result, dict) else None
    rate = result.get("hashrate_hs") if isinstance(result, dict) else None
    valid = (
        isinstance(result, dict)
        and result.get("mode") == "LOCAL_BENCHMARK_ONLY"
        and isinstance(count, int) and not isinstance(count, bool) and count > 0
        and isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool)
        and math.isfinite(elapsed) and elapsed > 0
        and isinstance(rate, (int, float)) and not isinstance(rate, bool)
        and math.isfinite(rate) and rate > 0
        and isinstance(digest, str) and len(digest) == 64
        and all(char in "0123456789abcdefABCDEF" for char in digest)
    )
    return make_layer_result(
        layer="cpu_reference",
        status="PASS" if valid else "FAIL",
        evidence={
            "execution_scope": "HOST_CPU_SOFTWARE_ONLY",
            "hashes_completed": count,
            "elapsed_seconds": elapsed,
            "hashrate_hs": rate,
            "last_digest_hex": digest,
            "rtl_verified": False,
            "pool_connected": False,
            "revenue_verified": False,
        } if valid else {},
        error_code=None if valid else "CPU_BENCHMARK_EVIDENCE_INCOMPLETE",
    )
