#!/usr/bin/env python3
"""Run the Electronic Brain simulation-first acceptance suite.

All actions stay inside temporary directories and emulators. This tool never
contacts real devices, starts VMs, provisions cloud resources, or reads secrets.
Every result is labelled SIMULATED and cannot satisfy a REAL boot gate.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
import sys
from pathlib import Path
from typing import Any

# Make direct invocation work from any current directory (Python sets sys.path[0] to tools/).
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from brain_v12.brain.arkan_device_emulator import ArkanDeviceEmulator
from brain_v12.brain.arkan_twin_golden_loop import ArkanTwinGoldenLoop
from brain_v12.brain.digital_twin_fabric import DigitalTwinFabric, Reality, RealityGate
from brain_v12.brain.powershell_emulator import PowerShellEmulator
from brain_v12.brain.desktop_commander_emulator import DesktopCommanderEmulator


def check(name: str, fn) -> dict[str, Any]:
    started = time.monotonic()
    try:
        details = fn()
        ok = bool(details.get("ok", False))
        return {"name": name, "ok": ok, "status": "PASS" if ok else "FAIL",
                "reality": "SIMULATED", "duration_ms": round((time.monotonic()-started)*1000, 2),
                "details": details}
    except Exception as exc:
        return {"name": name, "ok": False, "status": "ERROR", "reality": "SIMULATED",
                "duration_ms": round((time.monotonic()-started)*1000, 2),
                "error": f"{type(exc).__name__}: {exc}"}


def run_suite() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="brain-sim-suite-") as temp:
        root = Path(temp)
        results: list[dict[str, Any]] = []

        def twin_snapshot():
            fabric = DigitalTwinFabric(root / "twins")
            twin = fabric.create("sim-win2025")
            twin.emulator.write_file("boot-marker.txt", "SIMULATED_BOOT_ONLY")
            snap = twin.snapshot("baseline")
            restored = twin.restore_metadata(snap["snapshot"]["snapshot_id"])
            return {"ok": snap["ok"] and restored["ok"] and snap["snapshot"]["reality"] == "SIMULATED",
                    "snapshot_id": snap["snapshot"]["snapshot_id"], "sha256": snap["snapshot"]["sha256"]}

        results.append(check("digital_twin_snapshot_integrity", twin_snapshot))

        def powershell_sandbox():
            desktop = DesktopCommanderEmulator(root / "powershell", node_id="sim-win")
            ps = PowerShellEmulator(desktop)
            good = ps.run('New-Item report.txt; Set-Content report.txt -Value "BRAIN_SIM_OK"; Get-Content report.txt')
            denied = ps.run("Invoke-Expression 'whoami'")
            return {"ok": good["ok"] and "BRAIN_SIM_OK" in good["output"] and
                    not denied["ok"] and denied["errors"][0]["status"] == "COMMAND_NOT_SUPPORTED",
                    "supported_command_result": good["status"],
                    "unsupported_command_result": denied["errors"][0]["status"],
                    "unsupported_command_fail_closed": not denied["ok"]}

        results.append(check("powershell_emulator_sandbox", powershell_sandbox))

        def arkan_readiness_and_recovery():
            arkan = ArkanDeviceEmulator(root / "arkan")
            blocked = arkan.readiness()
            arkan.set_network(kvm=True)
            ready = arkan.readiness()
            arkan.inject_fault("network_down")
            faulted = arkan.readiness()
            arkan.clear_faults()
            recovered = arkan.readiness()
            return {"ok": (not blocked["ok"] and ready["ok"] and not faulted["ok"] and recovered["ok"]),
                    "initial_without_kvm": blocked["status"], "with_simulated_kvm": ready["status"],
                    "after_network_fault": faulted["status"], "after_recovery": recovered["status"],
                    "hardware_reality": "SIMULATED_NOT_HOST_INSPECTION"}

        results.append(check("arkan_twin_fault_and_recovery", arkan_readiness_and_recovery))

        def golden_closed_loop():
            with ArkanTwinGoldenLoop(root / "golden") as loop:
                loop.arkan.set_network(kvm=True)
                result = loop.run("Write-Output BRAIN_GOLDEN_SIM_OK; Get-ComputerInfo",
                                  task_id="brain-simulation-acceptance", max_attempts=2)
            return {"ok": bool(result.get("ok")) and
                    result.get("status") == "GOLDEN_CLOSED_LOOP_VERIFIED" and
                    result.get("transitions", [])[-1:] == ["CLOSED"],
                    "loop_status": result.get("status"),
                    "transitions": result.get("transitions"),
                    "evidence_count": len(result.get("evidence_ids", [])),
                    "reality": "SIMULATED"}

        results.append(check("golden_closed_loop", golden_closed_loop))

        def reality_separation():
            simulated = RealityGate.accept({"reality": "SIMULATED", "source": "digital-twin",
                                             "boot_verified": True}, Reality.REAL)
            correct = RealityGate.accept({"reality": "SIMULATED", "source": "digital-twin"}, Reality.SIMULATED)
            return {"ok": not simulated["ok"] and simulated["status"] == "REALITY_MISMATCH" and correct["ok"],
                    "simulated_cannot_prove_real_boot": not simulated["ok"],
                    "real_gate_status": simulated["status"]}

        results.append(check("reality_provenance_gate", reality_separation))

        passed = sum(1 for item in results if item["ok"])
        return {
            "schema": "electronic-brain.simulation-acceptance.v1",
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reality": "SIMULATED",
            "status": "PASS" if passed == len(results) else "FAIL",
            "checks_passed": passed,
            "checks_total": len(results),
            "real_windows_boot_verified": False,
            "cloud_resources_created": False,
            "real_devices_contacted": False,
            "secret_values_read": False,
            "acceptance_rule": "SIMULATED evidence validates emulator behavior only; Windows Server 2025 REAL boot and ASUS RDP require independent live evidence.",
            "checks": results,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Optional JSON evidence path")
    args = parser.parse_args()
    report = run_suite()
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
