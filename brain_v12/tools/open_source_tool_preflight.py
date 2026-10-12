"""Non-invasive preflight for optional open-source Brain tools.

This module only resolves executable paths via PATH. It never launches a process,
installs packages, downloads code, accesses the network, or touches hardware.
"""
from __future__ import annotations

import shutil
from typing import Callable

# Stable catalog IDs -> alternative executable names across common platforms.
EXECUTABLES: dict[str, tuple[str, ...]] = {
    "qemu": ("qemu-system-x86_64", "qemu-system-aarch64", "qemu-system-x86_64.exe", "qemu-img", "qemu-img.exe"),
    "ollama": ("ollama", "ollama.exe"),
    "llama_cpp": ("llama-server", "llama-server.exe"),
    "kicad": ("kicad-cli", "kicad-cli.exe"),
    "freecad": ("FreeCADCmd", "freecadcmd", "FreeCADCmd.exe"),
    "openocd": ("openocd", "openocd.exe"),
    "esptool": ("esptool", "esptool.exe", "esptool.py"),
    "avrdude": ("avrdude", "avrdude.exe"),
    "openems": ("openEMS", "openEMS.exe"),
}


def inspect_tool_availability(which: Callable[[str], str | None] = shutil.which) -> dict[str, object]:
    """Return PATH-based availability only; no executable is started."""
    tools = []
    for tool_id, candidates in EXECUTABLES.items():
        found = []
        for candidate in candidates:
            path = which(candidate)
            if path and path not in found:
                found.append(path)
        tools.append({
            "id": tool_id,
            "status": "available" if found else "not_found",
            "resolved_executables": found,
            "checked_names": list(candidates),
        })
    available = sum(item["status"] == "available" for item in tools)
    return {
        "ok": True,
        "mode": "path_preflight_only",
        "execution_enabled": False,
        "installation_enabled": False,
        "hardware_io_enabled": False,
        "summary": {"checked": len(tools), "available": available, "not_found": len(tools) - available},
        "tools": tools,
    }
