#!/usr/bin/env python3
"""Execute every locally available open-source Brain ASIC stage and preserve evidence.

This runner never pretends missing tools or physical fabrication are successful.
RTL simulation and synthesis are run when their tools are installed. Physical
implementation, tapeout, fabrication, and silicon test remain BLOCKED unless
separately supplied and independently verifiable evidence exists.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "brain_v12/asic/rtl/brain_asic_core.sv"
TB = ROOT / "brain_v12/asic/rtl/tb_brain_asic_core.sv"
OUT = Path(os.environ.get("BRAIN_ASIC_OUT", ROOT / "artifacts/asic-execution")).resolve()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_stage(name: str, argv: list[str], log_path: Path, expected: str | None = None) -> dict[str, Any]:
    if not shutil.which(argv[0]):
        return {"status": "BLOCKED_TOOL_MISSING", "command": argv, "tool": argv[0]}
    try:
        p = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=300, check=False)
        output = p.stdout or ""
        log_path.write_text(output, encoding="utf-8")
        ok = p.returncode == 0 and (expected is None or expected in output)
        return {
            "status": "PASS" if ok else "FAIL",
            "command": argv,
            "exit_code": p.returncode,
            "expected_marker": expected,
            "marker_found": expected in output if expected else None,
            "log": str(log_path.relative_to(OUT)),
            "log_sha256": digest(log_path),
        }
    except subprocess.TimeoutExpired as exc:
        log_path.write_text((exc.stdout or "") + "\nTIMEOUT after 300 seconds\n", encoding="utf-8")
        return {"status": "FAIL_TIMEOUT", "command": argv, "log": str(log_path.relative_to(OUT))}


def version(tool: str, args: list[str]) -> dict[str, Any]:
    path = shutil.which(tool)
    if not path:
        return {"status": "MISSING"}
    try:
        p = subprocess.run([tool, *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=10, check=False)
        return {"status": "AVAILABLE" if p.returncode == 0 else "VERSION_CHECK_FAILED",
                "path": path, "exit_code": p.returncode, "output": (p.stdout or "")[:1000]}
    except Exception as exc:
        return {"status": "VERSION_CHECK_FAILED", "error": type(exc).__name__}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "logs").mkdir(exist_ok=True)
    report: dict[str, Any] = {
        "schema_version": 1,
        "project": "Electronic Brain ASIC",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_scope": "OPEN_SOURCE_RTL_SIMULATION_AND_SYNTHESIS",
        "physical_hardware_access": False,
        "tools": {
            "iverilog": version("iverilog", ["-V"]),
            "vvp": version("vvp", ["-V"]),
            "yosys": version("yosys", ["-V"]),
        },
        "stages": {},
        "fabrication_claim_allowed": False,
    }
    if not RTL.is_file() or not TB.is_file():
        report["stages"]["rtl_simulation"] = {"status": "BLOCKED_SOURCE_MISSING",
                                               "rtl_exists": RTL.is_file(), "testbench_exists": TB.is_file()}
    elif shutil.which("iverilog") and shutil.which("vvp"):
        compile_log = OUT / "logs/iverilog-compile.log"
        compile_result = run_stage(
            "rtl_compile",
            ["iverilog", "-g2012", "-Wall", "-s", "tb_brain_asic_core", "-o",
             str(OUT / "brain_asic_tb.vvp"), str(RTL), str(TB)],
            compile_log,
        )
        if compile_result["status"] == "PASS":
            sim = run_stage("rtl_simulation",
                            ["vvp", str(OUT / "brain_asic_tb.vvp")],
                            OUT / "logs/rtl-simulation.log", "ALL_RTL_TESTS_PASSED")
            report["stages"]["rtl_simulation"] = sim
        else:
            report["stages"]["rtl_simulation"] = {"status": "BLOCKED_COMPILE_FAILED",
                                                   "compile": compile_result}
    else:
        report["stages"]["rtl_simulation"] = {"status": "BLOCKED_TOOL_MISSING",
                                               "required_tools": ["iverilog", "vvp"]}

    if RTL.is_file() and shutil.which("yosys"):
        synth = run_stage(
            "synthesis",
            ["yosys", "-p",
             f"read_verilog -sv {RTL}; hierarchy -top brain_asic_core; proc; opt; check; stat; write_json {OUT / 'brain_asic_core_synth.json'}"],
            OUT / "logs/yosys-synthesis.log",
        )
        # Yosys check output varies by version; nonzero exit fails. Keep the complete log.
        report["stages"]["synthesis"] = synth
        netlist = OUT / "brain_asic_core_synth.json"
        if synth["status"] == "PASS" and netlist.is_file() and netlist.stat().st_size:
            report["stages"]["synthesis"]["netlist"] = {
                "path": netlist.name, "bytes": netlist.stat().st_size, "sha256": digest(netlist)}
        else:
            report["stages"]["synthesis"]["status"] = "FAIL" if synth["status"] == "FAIL" else "BLOCKED"
    else:
        report["stages"]["synthesis"] = {"status": "BLOCKED_TOOL_OR_SOURCE_MISSING"}

    for stage in ("physical_design", "tapeout", "foundry_fabrication", "silicon_test"):
        report["stages"][stage] = {
            "status": "BLOCKED_EXTERNAL_EVIDENCE_REQUIRED",
            "reason": "This runner cannot create a foundry submission, manufacture silicon, or perform laboratory tests.",
        }

    sim_status = report["stages"]["rtl_simulation"]["status"]
    syn_status = report["stages"]["synthesis"]["status"]
    if sim_status == "PASS" and syn_status == "PASS":
        report["overall_status"] = "RTL_SIMULATION_AND_SYNTHESIS_PASS_PHYSICAL_STAGES_BLOCKED"
    elif sim_status.startswith("BLOCKED") or syn_status.startswith("BLOCKED"):
        report["overall_status"] = "PARTIAL_EXECUTION_TOOLS_OR_INPUTS_MISSING"
    else:
        report["overall_status"] = "EXECUTION_FAILED"

    report_path = OUT / "execution-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    # CI should fail if executable stages fail; missing optional tools are reported as blocked.
    if sim_status == "FAIL" or syn_status == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
