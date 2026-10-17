#!/usr/bin/env python3
"""Standalone evidence-first entry point for BRAIN-ASIC-001.

This wrapper reuses the repository's real Icarus Verilog RTL lab. It never
substitutes software hashing for RTL execution and never enables live mining.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "brain_v12" / "asic" / "sha256d_lab.py"
DEFAULT_OUT = ROOT / "artifacts" / "asic-unit-001"


def classify_evidence(evidence: dict[str, Any] | None) -> str:
    """Classify only RTL-lab evidence; never promote it to mining readiness."""
    if not evidence:
        return "BLOCKED_NO_RTL_EVIDENCE"
    tests = evidence.get("tests", [])
    statuses = [item.get("status") for item in tests]
    if evidence.get("final_status") == "SHA256D_RTL_PASS" and statuses and all(
        status == "PASS" for status in statuses
    ):
        return "RTL_SIMULATION_PASS_ONLY"
    if not statuses or "BLOCKED" in statuses or evidence.get("final_status") == "BLOCKED":
        return "BLOCKED"
    return "RTL_SIMULATION_FAIL"


def main() -> int:
    out = Path(os.environ.get("BRAIN_ASIC_UNIT_001_OUT", str(DEFAULT_OUT))).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    lab_log = out / "rtl-lab.log"
    lab_report = out / "sha256d-rtl-evidence.json"
    report_path = out / "unit-001-report.json"

    report: dict[str, Any] = {
        "schema": "electronic-brain-asic-unit-report/v1",
        "unit_id": "BRAIN-ASIC-001",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "RTL_SIMULATION_ONLY",
        "repository_root": str(ROOT),
        "lab_script": str(LAB.relative_to(ROOT)),
        "status": "BLOCKED",
        "lab_exit_code": None,
        "lab_report_path": str(lab_report),
        "lab_log_path": str(lab_log),
        "physical_device": "NOT_VERIFIED",
        "fabrication": "NOT_VERIFIED",
        "live_mining": "BLOCKED_NOT_IMPLEMENTED_IN_UNIT",
        "accepted_pool_shares": None,
        "measured_hashrate_hs": None,
        "measured_power_watts": None,
        "payout": None,
        "net_profit_jod": None,
        "network_access": False,
        "limitations": [
            "RTL simulation is not proof of physical ASIC fabrication or silicon testing.",
            "RTL simulation does not prove live pool mining, accepted shares, payout, or profit.",
            "This unit runner never connects to a mining pool or enables mining.",
        ],
    }

    if not LAB.is_file():
        report["status"] = "BLOCKED_LAB_SCRIPT_MISSING"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    try:
        proc = subprocess.run(
            [sys.executable, str(LAB), str(out)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        lab_log.write_text(
            (proc.stdout or "") + ("\n--- STDERR ---\n" + proc.stderr if proc.stderr else ""),
            encoding="utf-8",
        )
        report["lab_exit_code"] = proc.returncode
    except subprocess.TimeoutExpired as exc:
        lab_log.write_text("RTL lab timed out after 900 seconds.\n", encoding="utf-8")
        report["status"] = "RTL_LAB_TIMEOUT"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2

    evidence: dict[str, Any] | None = None
    if lab_report.is_file():
        try:
            evidence = json.loads(lab_report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            evidence = None

    report["rtl_evidence_status"] = classify_evidence(evidence)
    report["rtl_test_statuses"] = [
        {"name": test.get("name"), "status": test.get("status")}
        for test in (evidence or {}).get("tests", [])
    ]
    if report["rtl_evidence_status"] == "RTL_SIMULATION_PASS_ONLY":
        report["status"] = "RTL_SIMULATION_PASS_ONLY"
    elif report["rtl_evidence_status"] == "RTL_SIMULATION_FAIL":
        report["status"] = "RTL_SIMULATION_FAIL"
    else:
        report["status"] = "BLOCKED"

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "RTL_SIMULATION_PASS_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
