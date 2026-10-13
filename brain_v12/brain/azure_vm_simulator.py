"""Simulator-only Azure VM lifecycle model for Electronic Brain's Alexa cloud.

This module does not authenticate to Azure, create resources, or boot Windows.
Every result is explicitly marked simulated and real_boot_verified is always False.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AzureVmSpec:
    cloud_name: str = "alexa"
    vm_name: str = "alexa-windows-server-2025"
    region: str = "uaenorth"
    size: str = "Standard_D2s_v5"
    image: str = "WindowsServer:WindowsServer:2025-datacenter:latest"
    os_disk_gib: int = 128
    generation: int = 2
    accelerated_networking: bool = False


def simulate_vm(spec: AzureVmSpec | None = None) -> dict[str, Any]:
    """Return a deterministic plan; never contacts Azure or claims a real boot."""
    spec = spec or AzureVmSpec()
    checks = {
        "cloud_name_is_alexa": spec.cloud_name.strip().lower() == "alexa",
        "vm_name_present": bool(spec.vm_name.strip()),
        "region_present": bool(spec.region.strip()),
        "windows_server_2025_image": "windowsserver:windowsserver:2025-" in spec.image.lower(),
        "supported_generation": spec.generation == 2,
        "disk_capacity_positive": spec.os_disk_gib >= 64,
        "size_present": bool(spec.size.strip()),
    }
    ready = all(checks.values())
    return {
        "schema": "electronic-brain.azure-vm-simulation.v1",
        "cloud": spec.cloud_name,
        "provider": "Azure (simulated)",
        "simulation": True,
        "side_effects_performed": False,
        "azure_api_called": False,
        "resource_created": False,
        "vm": asdict(spec),
        "checks": checks,
        "status": "SIMULATED_PLAN_READY" if ready else "SIMULATED_PLAN_BLOCKED",
        "real_boot_verified": False,
        "boot_evidence": None,
        "next_step": (
            "Use an authenticated Azure deployment adapter and verify guest boot evidence."
            if ready else "Correct failed simulated configuration checks."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="-", help="JSON output path, or - for stdout")
    parser.add_argument("--region", default="uaenorth")
    parser.add_argument("--vm-name", default="alexa-windows-server-2025")
    parser.add_argument("--size", default="Standard_D2s_v5")
    args = parser.parse_args()
    result = simulate_vm(AzureVmSpec(region=args.region, vm_name=args.vm_name, size=args.size))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output == "-":
        print(rendered, end="")
    else:
        from pathlib import Path
        Path(args.output).write_text(rendered, encoding="utf-8")
        print(json.dumps({"output": args.output, "status": result["status"],
                          "simulation": True, "real_boot_verified": False}))
    return 0 if result["status"] == "SIMULATED_PLAN_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
