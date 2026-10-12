#!/usr/bin/env python3
"""Run an isolated, software-only Arkan simulator smoke test.

This does not require Desktop Commander, a physical PC, QEMU/KVM, or a cloud VM.
It proves only the Brain symbolic simulator works in this process; it never
claims a native Windows guest is installed or booted.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from brain_v12.virtual_hardware.arkan_provisioner import ARKAN_ID, provision_arkan


def run_smoke(registry_path: Path) -> dict:
    result = provision_arkan(registry_path)
    machine = result["machine"]
    machine.cpu.reset()
    execution = machine.execute(
        [("MOVI", 0, 2025), ("OUT", 0), ("HALT",)],
        max_cycles=10,
    )
    if execution.get("output") != [2025] or execution.get("halted") is not True:
        raise RuntimeError("ARKAN_SOFTWARE_NODE_SMOKE_FAILED")
    record = result["record"]
    return {
        "schema": "brain.arkan.software-node-smoke.v1",
        "status": "SIMULATION_READY",
        "node": {
            "name": "Arkan",
            "id": ARKAN_ID,
            "backend": "brain-simulator",
            "physical_host_required": False,
            "desktop_commander_required": False,
            "host_binding": None,
        },
        "smoke_test": {
            "status": "PASS",
            "workload": "symbolic_cpu_2025",
            "output": execution.get("output"),
            "halted": execution.get("halted"),
            "fidelity": "SIMULATED",
        },
        "windows_server_2025": {
            "installation_status": record["os_target"]["installation_status"],
            "boot_status": record["os_target"]["boot_status"],
            "native_os_boot_verified": False,
        },
        "host_resources_allocated": False,
        "system_state_changed": False,
        "registry_path": str(registry_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("arkan-software-node-report.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="brain-arkan-software-") as tmp:
        report = run_smoke(Path(tmp) / "arkan.json")
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
