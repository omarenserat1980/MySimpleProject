"""Bounded, evidence-first adapter for executing the repository's Bitcoin RTL testbench.

This runs Icarus Verilog/VVP as subprocesses. It never substitutes Python hashing
for RTL execution and never claims physical hardware, pool, share, or revenue proof.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
RTL_DIR = ROOT / "brain_v12" / "asic" / "rtl"
RTL_SOURCES = (
    "sha256_compress.sv",
    "sha256d_header_hash.sv",
    "bitcoin_pow_target_check.sv",
    "bitcoin_nonce_sweep.sv",
    "tb_bitcoin_genesis_nonce_search.sv",
)
EXPECTED_MARKER = "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED"
EXPECTED_NONCE = "7c2bac1d"
DEFAULT_TIMEOUT_SECONDS = 20.0


def _run_process(
    command: list[str], *, cwd: str, timeout_seconds: float,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    """Run a child process with a hard timeout and cooperative cancellation."""
    process = subprocess.Popen(
        command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    started = time.monotonic()
    while True:
        if cancel_check is not None and cancel_check():
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr), "CANCELLED"
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr), None
        if time.monotonic() - started >= timeout_seconds:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(command, process.returncode, stdout, stderr), "TIMEOUT"
        time.sleep(0.02)


def run_sha256d_rtl_self_test(
    *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Run a fixed known-answer RTL test; fail closed if tools/output/evidence are missing."""
    base: dict[str, Any] = {
        "contract_version": "brain.sha256d.execution.v1",
        "algorithm": "SHA-256d",
        "execution_mode": "RTL_SIMULATION",
        "rtl_executed": False,
        "software_hashing_substituted": False,
        "physical_asic_executed": False,
        "pool_contacted": False,
        "share_submitted": False,
        "pool_acceptance_verified": False,
        "revenue_verified": False,
        "evidence_status": "BLOCKED",
    }
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0.1 <= timeout_seconds <= 120:
        return {**base, "status": "INVALID_TIMEOUT", "error_code": "TIMEOUT_OUT_OF_RANGE"}
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    if not iverilog or not vvp:
        return {
            **base,
            "status": "BLOCKED_TOOLCHAIN_UNAVAILABLE",
            "error_code": "IVERILOG_OR_VVP_NOT_FOUND",
            "toolchain": {"iverilog_available": bool(iverilog), "vvp_available": bool(vvp)},
        }
    missing = [name for name in RTL_SOURCES if not (RTL_DIR / name).is_file()]
    if missing:
        return {**base, "status": "BLOCKED_RTL_SOURCE_MISSING", "missing_sources": missing}

    import tempfile

    deadline = time.monotonic() + float(timeout_seconds)
    try:
        with tempfile.TemporaryDirectory(prefix="brain-rtl-") as temp_dir:
            output = str(Path(temp_dir) / "genesis-search.vvp")
            compile_cmd = [
                iverilog, "-g2012", "-Wall", "-s", "tb_bitcoin_genesis_nonce_search",
                "-o", output, *(str(RTL_DIR / name) for name in RTL_SOURCES),
            ]
            compile_remaining = deadline - time.monotonic()
            if compile_remaining <= 0:
                return {**base, "status": "RTL_COMPILE_TIMEOUT", "error_code": "OVERALL_TIMEOUT"}
            compiled, compile_stop = _run_process(
                compile_cmd, cwd=str(ROOT), timeout_seconds=compile_remaining,
                cancel_check=cancel_check,
            )
            if compile_stop == "CANCELLED":
                return {**base, "status": "RTL_CANCELLED", "error_code": "CANCELLED_DURING_COMPILE"}
            if compile_stop == "TIMEOUT":
                return {**base, "status": "RTL_COMPILE_TIMEOUT", "error_code": "IVERILOG_TIMEOUT"}
            if compiled is None or compiled.returncode != 0:
                return {
                    **base, "status": "RTL_COMPILE_FAILED", "error_code": "IVERILOG_NONZERO_EXIT",
                    "return_code": compiled.returncode,
                    "stderr_tail": (compiled.stderr or "")[-2000:],
                }
            simulation_remaining = deadline - time.monotonic()
            if simulation_remaining <= 0:
                return {**base, "status": "RTL_SIMULATION_TIMEOUT", "error_code": "OVERALL_TIMEOUT"}
            simulated, simulation_stop = _run_process(
                [vvp, output], cwd=str(ROOT), timeout_seconds=simulation_remaining,
                cancel_check=cancel_check,
            )
            if simulation_stop == "CANCELLED":
                return {**base, "status": "RTL_CANCELLED", "error_code": "CANCELLED_DURING_SIMULATION"}
            if simulation_stop == "TIMEOUT":
                return {**base, "status": "RTL_SIMULATION_TIMEOUT", "error_code": "VVP_TIMEOUT"}
            if simulated is None:
                return {**base, "status": "RTL_RESULT_UNVERIFIED", "error_code": "SIMULATOR_RESULT_MISSING"}
            log = (simulated.stdout or "") + "\n" + (simulated.stderr or "")
            nonce_match = re.search(r"PASS BITCOIN_GENESIS_NONCE_FOUND nonce=([0-9a-fA-F]{8}) attempts=(\d+)", log)
            passed = (
                simulated.returncode == 0
                and EXPECTED_MARKER in log
                and nonce_match is not None
                and nonce_match.group(1).lower() == EXPECTED_NONCE
                and int(nonce_match.group(2)) == 2
            )
            if not passed:
                return {
                    **base, "status": "RTL_RESULT_UNVERIFIED", "error_code": "EXPECTED_PASS_EVIDENCE_MISSING",
                    "return_code": simulated.returncode,
                    "pass_marker_found": EXPECTED_MARKER in log,
                    "expected_nonce_found": bool(nonce_match and nonce_match.group(1).lower() == EXPECTED_NONCE),
                    "log_tail": log[-3000:],
                }
            return {
                **base,
                "status": "VERIFIED",
                "rtl_executed": True,
                "evidence_status": "RTL_SIMULATION_VERIFIED",
                "toolchain": {"iverilog": Path(iverilog).name, "vvp": Path(vvp).name},
                "testbench": "tb_bitcoin_genesis_nonce_search",
                "known_answer": {"nonce_hex": EXPECTED_NONCE, "attempts": 2},
                "pass_marker": EXPECTED_MARKER,
                "evidence": {
                    "compile_return_code": compiled.returncode,
                    "simulation_return_code": simulated.returncode,
                    "pass_marker_observed": True,
                    "expected_nonce_observed": True,
                },
            }
    except OSError as exc:
        return {**base, "status": "RTL_TOOL_EXECUTION_FAILED", "error_code": type(exc).__name__}
