"""Canonical software-only Arkan node with Brain-managed app emulators.

This facade deliberately exposes emulator APIs, never native Desktop Commander,
PowerShell, or a physical-host execution channel.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .arkan_device_emulator import ArkanDeviceEmulator, ArkanProfile
from .digital_twin_fabric import Reality

SCHEMA = "brain.arkan-software-node.v1"
NODE_ID = "arkan-virtual-01"


class ArkanSoftwareNode:
    """Canonical Arkan node; Desktop Commander and PowerShell are emulated apps."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        profile = ArkanProfile(
            device_id=NODE_ID,
            name=NODE_ID,
            os="BRAIN Virtual Windows",
            build="BRAIN-SOFTWARE-NODE",
            model="Electronic Brain Virtual Computer",
            logical_cpus=8,
            ram_gib=3.0,
            architecture="x64",
            wsl_distribution="brain-linux-sandbox",
            wsl_version=2,
            labels=[
                "canonical-virtual-node",
                "software-only",
                "desktop-commander-emulator",
                "powershell-emulator",
                "no-physical-host-required",
            ],
        )
        self.runtime = ArkanDeviceEmulator(self.root, profile)
        self.connected = False

    def connect(self) -> dict[str, Any]:
        self.connected = True
        self.runtime.services["BrainAgent"] = "RUNNING"
        self.runtime.services["DesktopCommanderEmulator"] = "RUNNING"
        self.runtime.services["PowerShellEmulator"] = "RUNNING"
        self.runtime.services["NativeDesktopCommander"] = "NOT_USED"
        self.runtime.services["NativePowerShell"] = "NOT_USED"
        return self.status()

    def status(self) -> dict[str, Any]:
        desktop = self.runtime.desktop.info()
        powershell = self.runtime.powershell.info()
        return {
            "ok": self.connected,
            "schema": SCHEMA,
            "node_id": NODE_ID,
            "node_type": "SOFTWARE_ONLY",
            "connected": self.connected,
            "physical_host_required": False,
            "native_desktop_commander_used": False,
            "native_powershell_used": False,
            "reality": Reality.SIMULATED.value,
            "indicator_state": "READY_SIMULATED" if self.connected else "NOT_CONNECTED",
            "execution_eligible": False,
            "apps": {
                "desktop_commander": {
                    "implementation": "DesktopCommanderEmulator",
                    "schema": desktop.get("schema"),
                    "ready": bool(self.connected and desktop.get("ok")),
                },
                "powershell": {
                    "implementation": "PowerShellEmulator",
                    "schema": powershell.get("schema"),
                    "ready": bool(self.connected and powershell.get("ok")),
                },
            },
            "services": dict(self.runtime.services),
            "vms": dict(self.runtime.vms),
            "warning": "Simulation status is not proof of a real Windows Server boot.",
        }

    def heartbeat(self) -> dict[str, Any]:
        if not self.connected:
            return {"ok": False, "status": "NODE_NOT_CONNECTED", "node_id": NODE_ID,
                    "reality": Reality.SIMULATED.value}
        result = self.runtime.heartbeat()
        return {**result, "node_id": NODE_ID, "reality": Reality.SIMULATED.value,
                "node_type": "SOFTWARE_ONLY"}

    def desktop_info(self) -> dict[str, Any]:
        return self.runtime.desktop.info()

    def desktop_list(self, path: str = ".") -> dict[str, Any]:
        return self.runtime.desktop.list_dir(path)

    def desktop_write(self, path: str, content: str) -> dict[str, Any]:
        return self.runtime.desktop.write_file(path, content)

    def desktop_read(self, path: str) -> dict[str, Any]:
        return self.runtime.desktop.read_file(path)

    def powershell_info(self) -> dict[str, Any]:
        return self.runtime.powershell.info()

    def run_powershell(self, script: str) -> dict[str, Any]:
        if not self.connected:
            return {"ok": False, "status": "NODE_NOT_CONNECTED",
                    "reality": Reality.SIMULATED.value}
        result = self.runtime.powershell.run(script)
        return {**result, "node_id": NODE_ID, "reality": Reality.SIMULATED.value,
                "execution_channel": "BRAIN_POWERSHELL_EMULATOR"}

    def audit(self) -> dict[str, Any]:
        return {
            "ok": True,
            "node_id": NODE_ID,
            "root": str(self.root),
            "native_tools_invoked": False,
            "physical_host_contacted": False,
            "reality": Reality.SIMULATED.value,
        }
