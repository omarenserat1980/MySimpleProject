"""Read-only discovery of Electronic Brain's local software nodes.

This module inventories software capabilities and repository components without
starting processes, contacting networks, reading secret values, or claiming that
simulated/installed components are live executors.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# Import availability is evidence of an installed module, not proof of runtime health.
MODULES = (
    "fastapi", "uvicorn", "pytest", "psutil", "torch", "tensorflow",
    "numpy", "cv2", "PIL", "requests", "httpx", "yaml",
)
EXECUTABLES = (
    "python", "python3", "git", "ffmpeg", "ffprobe", "adb",
    "qemu-system-x86_64", "qemu-img", "iverilog", "verilator",
)
COMPONENT_PATHS = (
    "brain_v12/brain/capability_registry.py",
    "brain_v12/brain/tool_foundry.py",
    "brain_v12/self_healing/improvement_engine.py",
    "brain_v12/self_healing/review_loop.py",
    "brain_v12/VIRTUAL_COMPUTER_ARCHITECTURE.md",
    "brain_v12/brain/braiins_mining_observer.py",
    "brain_v12/brain/mining_evidence_ledger.py",
    "brain_v12/tools/braiins_pool_readonly_diagnostics.py",
)


def _module_status(name: str) -> dict[str, Any]:
    try:
        spec = importlib.util.find_spec(name)
        return {"name": name, "available": spec is not None}
    except (ImportError, ValueError, ModuleNotFoundError):
        return {"name": name, "available": False}


def _executable_status(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"name": name, "available": path is not None, "path": path}


def _component_status(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return {"path": relative, "present": path.is_file()}


def discover() -> dict[str, Any]:
    """Return a JSON-safe inventory with explicit evidence boundaries."""
    return {
        "schema": "brain-software-node-inventory/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_LOCAL_DISCOVERY",
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "cpu_logical_count": os.cpu_count(),
        },
        "python_modules": [_module_status(name) for name in MODULES],
        "executables": [_executable_status(name) for name in EXECUTABLES],
        "brain_components": [_component_status(path) for path in COMPONENT_PATHS],
        "safety": {
            "network_probed": False,
            "processes_started": False,
            "secrets_read": False,
            "files_modified_by_discovery": False,
            "installed_means_healthy": False,
            "simulated_means_physical": False,
            "mining_active_claimed": False,
        },
        "interpretation": (
            "Presence indicates local software or a repository file only. "
            "It does not prove that a service is running, a remote device is "
            "reachable, a mining worker is connected, or revenue was realized."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional new JSON report path; refuses overwrite.")
    args = parser.parse_args(argv)
    report = discover()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        if output.exists():
            parser.error(f"refusing to overwrite existing file: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
