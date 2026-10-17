#!/usr/bin/env python3
"""Run known-answer RTL tests for Bitcoin SHA-256d hashing and bounded nonce search.

This gate invokes real Icarus Verilog binaries; it never substitutes Python hashing
for RTL execution and never claims physical ASIC, pool, or mining evidence.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "brain_v12/asic/rtl"
OUT_DEFAULT = ROOT / "artifacts/asic-digital-lab/sha256d"


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_test(name: str, top: str, sources: list[str], marker: str, out: Path) -> dict[str, Any]:
    compile_log = out / f"{name}-compile.log"
    run_log = out / f"{name}-run.log"
    binary = out / f"{name}.vvp"
    source_paths = [RTL / source for source in sources]
    result: dict[str, Any] = {
        "name": name,
        "top": top,
        "sources": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
            for path in source_paths
        ],
        "required_marker": marker,
        "status": "BLOCKED",
    }
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        missing = [tool for tool in ("iverilog", "vvp") if not shutil.which(tool)]
        result["error"] = "Required executable(s) missing: " + ", ".join(missing)
        compile_log.write_text(result["error"] + "\n", encoding="utf-8")
        return result
    missing_sources = [str(path) for path in source_paths if not path.is_file()]
    if missing_sources:
        result["error"] = "Missing source file(s): " + ", ".join(missing_sources)
        compile_log.write_text(result["error"] + "\n", encoding="utf-8")
        return result

    compile_cmd = [
        "iverilog", "-g2012", "-s", top, "-o", str(binary),
        *[str(path) for path in source_paths],
    ]
    try:
        compiled = subprocess.run(
            compile_cmd, cwd=ROOT, capture_output=True, text=True,
            timeout=120, check=False,
        )
    except subprocess.TimeoutExpired:
        compile_log.write_text("TIMEOUT compiling RTL after 120 seconds\n", encoding="utf-8")
        result.update({"status": "FAIL", "compile_returncode": None, "error": "COMPILE_TIMEOUT"})
        return result
    compile_output = (compiled.stdout or "") + (compiled.stderr or "")
    compile_log.write_text(compile_output, encoding="utf-8")
    result["compile_command"] = compile_cmd
    result["compile_returncode"] = compiled.returncode
    result["compile_log"] = str(compile_log.relative_to(ROOT))
    if compiled.returncode != 0:
        result.update({"status": "FAIL", "error": "RTL compilation failed"})
        return result

    try:
        ran = subprocess.run(
            ["vvp", str(binary)], cwd=ROOT, capture_output=True, text=True,
            timeout=300, check=False,
        )
    except subprocess.TimeoutExpired:
        run_log.write_text("TIMEOUT executing RTL simulation after 300 seconds\n", encoding="utf-8")
        result.update({"status": "FAIL", "run_returncode": None, "error": "SIMULATION_TIMEOUT"})
        return result
    run_output = (ran.stdout or "") + (ran.stderr or "")
    run_log.write_text(run_output, encoding="utf-8")
    result["run_command"] = ["vvp", str(binary)]
    result["run_returncode"] = ran.returncode
    result["run_log"] = str(run_log.relative_to(ROOT))
    result["pass_marker_seen"] = marker in run_output
    result["output_tail"] = run_output[-2500:]
    result["status"] = "PASS" if ran.returncode == 0 and marker in run_output else "FAIL"
    if result["status"] != "PASS":
        result["error"] = "Simulation failed or expected pass marker was absent"
    return result


def main() -> int:
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else OUT_DEFAULT
    out.mkdir(parents=True, exist_ok=True)
    tests = [
        (
            "sha256d-genesis-header",
            "tb_sha256d_header_hash",
            ["sha256_compress.sv", "sha256d_header_hash.sv", "tb_sha256d_header_hash.sv"],
            "ALL_SHA256D_HEADER_RTL_TESTS_PASSED",
        ),
        (
            "bitcoin-target-check",
            "tb_bitcoin_pow_target_check",
            ["bitcoin_pow_target_check.sv", "tb_bitcoin_pow_target_check.sv"],
            "ALL_BITCOIN_TARGET_CHECK_TESTS_PASSED",
        ),
        (
            "bounded-nonce-sweep",
            "tb_bitcoin_nonce_sweep",
            [
                "sha256_compress.sv", "sha256d_header_hash.sv",
                "bitcoin_pow_target_check.sv", "bitcoin_nonce_sweep.sv",
                "tb_bitcoin_nonce_sweep.sv",
            ],
            "ALL_NONCE_SWEEP_TESTS_PASSED",
        ),
        (
            "genesis-nonce-search",
            "tb_bitcoin_genesis_nonce_search",
            [
                "sha256_compress.sv", "sha256d_header_hash.sv",
                "bitcoin_pow_target_check.sv", "bitcoin_nonce_sweep.sv",
                "tb_bitcoin_genesis_nonce_search.sv",
            ],
            "ALL_GENESIS_NONCE_SEARCH_TESTS_PASSED",
        ),
    ]
    evidence: dict[str, Any] = {
        "schema": "electronic-brain-sha256d-rtl-lab/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "commit_sha": None,
        "scope": "RTL_SIMULATION_ONLY",
        "physical_hardware_access": False,
        "fabrication": "NOT_PERFORMED",
        "tool_versions": {},
        "tests": [],
        "final_status": "BLOCKED",
        "limitations": [
            "Passing known-answer RTL tests do not prove exhaustive correctness or measured hashrate.",
            "This gate does not connect to a pool, submit shares, fabricate silicon, or prove revenue.",
        ],
    }
    for tool, command in (("iverilog", ["iverilog", "-V"]), ("vvp", ["vvp", "-V"])):
        if shutil.which(tool):
            try:
                proc = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
                evidence["tool_versions"][tool] = {
                    "status": "AVAILABLE" if proc.returncode == 0 else "VERSION_CHECK_FAILED",
                    "version": ((proc.stdout or proc.stderr).strip().splitlines() or [""])[0][:300],
                    "returncode": proc.returncode,
                }
            except (OSError, subprocess.TimeoutExpired) as exc:
                evidence["tool_versions"][tool] = {"status": "VERSION_CHECK_FAILED", "error": type(exc).__name__}
        else:
            evidence["tool_versions"][tool] = {"status": "MISSING"}

    evidence["tests"] = [run_test(*test, out) for test in tests]
    statuses = [test["status"] for test in evidence["tests"]]
    evidence["final_status"] = (
        "SHA256D_RTL_PASS" if statuses and all(s == "PASS" for s in statuses)
        else "BLOCKED" if "BLOCKED" in statuses
        else "FAIL"
    )
    manifest = out / "sha256d-rtl-evidence.json"
    manifest.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    print(evidence["final_status"])
    return 0 if evidence["final_status"] == "SHA256D_RTL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
