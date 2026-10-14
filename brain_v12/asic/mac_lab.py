#!/usr/bin/env python3
"""Run actual simulation and Yosys synthesis for the experimental signed MAC RTL."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "brain_v12/asic/rtl/brain_mac_accelerator.sv"
TB = ROOT / "brain_v12/asic/rtl/tb_brain_mac_accelerator.sv"


def digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name: str, command: list[str], log: Path, timeout: int = 300) -> dict:
    if shutil.which(command[0]) is None:
        log.write_text(f"BLOCKED: missing executable {command[0]}\n", encoding="utf-8")
        return {"status": "BLOCKED", "command": command, "log": str(log)}
    try:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        output = (proc.stdout or "") + (proc.stderr or "")
        log.write_text(output, encoding="utf-8", errors="replace")
        return {"status": "PASS" if proc.returncode == 0 else "FAIL",
                "returncode": proc.returncode, "command": command, "log": str(log),
                "output_tail": output[-2000:]}
    except subprocess.TimeoutExpired:
        log.write_text(f"FAIL: timeout after {timeout}s\n", encoding="utf-8")
        return {"status": "FAIL", "command": command, "log": str(log), "error": "TIMEOUT"}


def main() -> int:
    out = (ROOT / "artifacts/asic-digital-lab").resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "tool": "Brain MAC Accelerator Lab",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "SIGNED_MAC_RTL_SIMULATION_AND_SYNTHESIS_ONLY",
        "fabrication": "NOT_PERFORMED",
        "sources": {"rtl": str(RTL), "rtl_sha256": digest(RTL),
                    "testbench": str(TB), "testbench_sha256": digest(TB)},
        "simulation": {"status": "NOT_RUN"},
        "synthesis": {"status": "NOT_RUN"},
        "final_status": "BLOCKED",
    }
    if not RTL.is_file() or not TB.is_file():
        manifest["error"] = "MAC RTL or testbench missing"
        (out / "mac-lab-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps(manifest, indent=2))
        return 2

    binary = out / "brain_mac_accelerator.vvp"
    compile_result = run("iverilog_compile",
        ["iverilog", "-g2012", "-s", "tb_brain_mac_accelerator", "-o", str(binary), str(RTL), str(TB)],
        out / "mac-iverilog-compile.log")
    manifest["simulation"]["compile"] = compile_result
    if compile_result["status"] == "PASS":
        sim = run("iverilog_run", ["vvp", str(binary)], out / "mac-simulation.log")
        if sim["status"] == "PASS":
            output = (out / "mac-simulation.log").read_text(encoding="utf-8", errors="replace")
            if "ALL_MAC_TESTS_PASSED" not in output:
                sim["status"] = "FAIL"
                sim["error"] = "Missing ALL_MAC_TESTS_PASSED marker"
            else:
                sim["pass_marker"] = "ALL_MAC_TESTS_PASSED"
        manifest["simulation"]["run"] = sim
        manifest["simulation"]["status"] = sim["status"]
    else:
        manifest["simulation"]["status"] = compile_result["status"]

    netlist = out / "brain_mac_accelerator_synth.json"
    script = (f"read_verilog -sv {RTL}; hierarchy -check -top brain_mac_accelerator; "
              "proc; opt; check; synth -top brain_mac_accelerator; check; stat; "
              f"write_json {netlist}")
    synthesis = run("yosys_synthesis", ["yosys", "-p", script], out / "mac-yosys-synthesis.log", timeout=600)
    if synthesis["status"] == "PASS":
        if netlist.is_file() and netlist.stat().st_size > 0:
            synthesis["netlist_size_bytes"] = netlist.stat().st_size
            synthesis["netlist_sha256"] = digest(netlist)
        else:
            synthesis["status"] = "FAIL"
            synthesis["error"] = "No non-empty synthesized netlist was produced"
    manifest["synthesis"] = synthesis
    manifest["final_status"] = ("MAC_DIGITAL_LAB_PASS"
        if manifest["simulation"]["status"] == "PASS" and synthesis["status"] == "PASS"
        else "FAIL" if "FAIL" in (manifest["simulation"]["status"], synthesis["status"])
        else "BLOCKED")
    manifest["limitations"] = [
        "Simulation and synthesis do not prove formal correctness or physical silicon.",
        "PPA and energy are not claimed unless separately measured and documented.",
    ]
    (out / "mac-lab-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["final_status"] == "MAC_DIGITAL_LAB_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
