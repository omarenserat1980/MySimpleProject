"""Read-only probe for optional ASIC/RTL tools; never installs or provisions anything."""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

TOOLS = {
    "iverilog": ["iverilog", "-V"],
    "verilator": ["verilator", "--version"],
    "yosys": ["yosys", "-V"],
}


def probe_toolchain() -> dict[str, Any]:
    """Report actual tool availability and version-command results."""
    results: dict[str, Any] = {}
    for name, command in TOOLS.items():
        executable = shutil.which(name)
        if executable is None:
            results[name] = {
                "status": "MISSING",
                "executable": None,
                "version": None,
                "returncode": None,
            }
            continue
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            output = (completed.stdout or completed.stderr).strip().splitlines()
            results[name] = {
                "status": "AVAILABLE" if completed.returncode == 0 else "VERSION_CHECK_FAILED",
                "executable": executable,
                "version": output[0][:300] if output else "NO_VERSION_OUTPUT",
                "returncode": completed.returncode,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            results[name] = {
                "status": "VERSION_CHECK_FAILED",
                "executable": executable,
                "version": None,
                "returncode": None,
                "error": type(exc).__name__,
            }
    return {
        "schema_version": 1,
        "scope": "LOCAL_TOOL_DISCOVERY_ONLY",
        "physical_hardware_access": False,
        "tools": results,
        "interpretation": (
            "Tool presence does not prove RTL correctness, synthesis success, "
            "FPGA availability, or physical ASIC readiness."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(probe_toolchain(), indent=2, sort_keys=True))
