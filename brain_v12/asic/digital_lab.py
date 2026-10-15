#!/usr/bin/env python3
"""Run the real RTL simulation and Yosys synthesis gates for Brain's digital ASIC lab.

This tool never emulates a passing hardware result in Python. If a required EDA
binary is missing or a command fails, the evidence manifest records BLOCKED/FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RTL = ROOT / "brain_v12/asic/rtl/brain_asic_core.sv"
DEFAULT_TB = ROOT / "brain_v12/asic/rtl/tb_brain_asic_core.sv"


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(name: str, command: list[str], log_path: Path, timeout: int = 300) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        log_path.write_text(f"BLOCKED: executable not found: {command[0]}\n", encoding="utf-8")
        return {"status": "BLOCKED", "command": command, "returncode": None, "log": str(log_path)}
    try:
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "command": command,
            "executable": executable,
            "returncode": completed.returncode,
            "log": str(log_path),
            "output_tail": output[-3000:],
        }
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        output += "\nTIMEOUT: command exceeded " + str(timeout) + " seconds\n"
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return {"status": "FAIL", "command": command, "returncode": None, "log": str(log_path), "error": "TIMEOUT"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", type=Path, default=DEFAULT_RTL)
    parser.add_argument("--testbench", type=Path, default=DEFAULT_TB)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/asic-digital-lab")
    args = parser.parse_args()

    rtl = args.rtl.resolve()
    tb = args.testbench.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "digital-asic-lab-manifest.json"
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "tool": "Electronic Brain Digital ASIC Lab",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "DIGITAL_RTL_SIMULATION_AND_LOGIC_SYNTHESIS_ONLY",
        "physical_hardware_access": False,
        "fabrication": "NOT_PERFORMED",
        "source": {
            "rtl": str(rtl),
            "rtl_sha256": sha256(rtl),
            "testbench": str(tb),
            "testbench_sha256": sha256(tb),
        },
        "simulation": {"status": "NOT_RUN"},
        "synthesis": {"status": "NOT_RUN"},
        "final_status": "BLOCKED",
        "limitations": [
            "A passing simulation does not prove all possible input sequences are correct.",
            "A successful synthesis does not prove physical timing, foundry signoff, or manufactured silicon.",
        ],
    }

    if not rtl.is_file() or not tb.is_file():
        evidence["error"] = "RTL or testbench file is missing."
        manifest_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2))
        return 2

    sim_binary = out / "brain_asic_core.vvp"
    sim_compile = run_command(
        "iverilog_compile",
        ["iverilog", "-g2012", "-s", "tb_brain_asic_core", "-o", str(sim_binary), str(rtl), str(tb)],
        out / "iverilog-compile.log",
    )
    evidence["simulation"]["compile"] = sim_compile
    if sim_compile["status"] == "PASS":
        sim_run = run_command("iverilog_run", ["vvp", str(sim_binary)], out / "rtl-simulation.log")
        if sim_run["status"] == "PASS":
            sim_log = (out / "rtl-simulation.log").read_text(encoding="utf-8", errors="replace")
            if "ALL_RTL_TESTS_PASSED" not in sim_log:
                sim_run["status"] = "FAIL"
                sim_run["error"] = "Expected ALL_RTL_TESTS_PASSED marker was not found."
            else:
                sim_run["pass_marker"] = "ALL_RTL_TESTS_PASSED"
        evidence["simulation"]["run"] = sim_run
        evidence["simulation"]["status"] = (
            "PASS" if sim_compile["status"] == "PASS" and sim_run["status"] == "PASS" else "FAIL"
        )
    else:
        evidence["simulation"]["status"] = sim_compile["status"]

    netlist = out / "brain_asic_core_synth.json"
    yosys_script = (
        f"read_verilog -sv {rtl}; "
        "hierarchy -check -top brain_asic_core; "
        "proc; opt; check; "
        "synth -top brain_asic_core; check; stat; "
        f"write_json {netlist}"
    )
    synth = run_command("yosys_synthesis", ["yosys", "-p", yosys_script], out / "yosys-synthesis.log", timeout=600)
    if synth["status"] == "PASS":
        if netlist.is_file() and netlist.stat().st_size > 0:
            synth["netlist"] = str(netlist)
            synth["netlist_size_bytes"] = netlist.stat().st_size
            synth["netlist_sha256"] = sha256(netlist)
        else:
            synth["status"] = "FAIL"
            synth["error"] = "Yosys returned success but no non-empty JSON netlist was produced."
    evidence["synthesis"] = synth

    if evidence["simulation"]["status"] == "PASS" and evidence["synthesis"]["status"] == "PASS":
        evidence["final_status"] = "DIGITAL_ASIC_LAB_PASS"
    elif "BLOCKED" in (evidence["simulation"]["status"], evidence["synthesis"]["status"]):
        evidence["final_status"] = "BLOCKED"
    else:
        evidence["final_status"] = "FAIL"

    manifest_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    print(evidence["final_status"])
    return 0 if evidence["final_status"] == "DIGITAL_ASIC_LAB_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
