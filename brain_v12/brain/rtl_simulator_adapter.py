"""Bounded, evidence-first adapter for executing the repository's Bitcoin RTL testbench.

This runs Icarus Verilog/VVP as subprocesses. It never substitutes Python hashing
for RTL execution and never claims physical hardware, pool, share, or revenue proof.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


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


def run_sha256d_rtl_self_test(*, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
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

    try:
        with tempfile.TemporaryDirectory(prefix="brain-rtl-") as temp_dir:
            output = str(Path(temp_dir) / "genesis-search.vvp")
            compile_cmd = [
                iverilog, "-g2012", "-Wall", "-s", "tb_bitcoin_genesis_nonce_search",
                "-o", output, *(str(RTL_DIR / name) for name in RTL_SOURCES),
            ]
            compiled = subprocess.run(
                compile_cmd, cwd=str(ROOT), capture_output=True, text=True,
                timeout=float(timeout_seconds), check=False,
            )
            if compiled.returncode != 0:
                return {
                    **base, "status": "RTL_COMPILE_FAILED", "error_code": "IVERILOG_NONZERO_EXIT",
                    "return_code": compiled.returncode,
                    "stderr_tail": (compiled.stderr or "")[-2000:],
                }
            try:
                simulated = subprocess.run(
                    [vvp, output], cwd=str(ROOT), capture_output=True, text=True,
                    timeout=float(timeout_seconds), check=False,
                )
            except subprocess.TimeoutExpired:
                return {**base, "status": "RTL_SIMULATION_TIMEOUT", "error_code": "VVP_TIMEOUT"}
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
    except subprocess.TimeoutExpired:
        return {**base, "status": "RTL_COMPILE_TIMEOUT", "error_code": "IVERILOG_TIMEOUT"}
    except OSError as exc:
        return {**base, "status": "RTL_TOOL_EXECUTION_FAILED", "error_code": type(exc).__name__}
