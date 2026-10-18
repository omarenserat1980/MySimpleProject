from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .windows_iso_fetch import download_official_windows_iso


@dataclass
class QemuWindowsBackend:
    """Brain-controlled QEMU backend for a real Windows Server guest.

    When iso_url is configured, media is fetched on the executor host (not the
    Android phone), resumed when HTTP byte ranges are supported, and SHA-256
    verified before QEMU is allowed to use it. The URL is never included in
    status output because Microsoft's direct URLs can contain temporary tokens.
    """
    qemu_binary: str = "qemu-system-x86_64"
    memory: str = "4G"
    cpus: int = 2
    machine: str = "q35"
    disk_path: str | None = None
    iso_path: str | None = None
    iso_url: str | None = None
    iso_sha256: str | None = None
    iso_cache_dir: str = "~/.cache/brain/windows"

    def available(self) -> bool:
        return shutil.which(self.qemu_binary) is not None

    def prepare_iso(self) -> dict:
        """Real media preparation is disabled; use the software simulator."""
        raise RuntimeError("WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY")

    def command(self, install: bool = True) -> list[str]:
        raise RuntimeError("WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY")

    def inspect(self) -> dict:
        return {
            "ok": True,
            "backend": "software-simulator-only",
            "available": False,
            "binary": None,
            "execution_mode": "SIMULATION_ONLY",
            "real_windows_boot_verified": False,
            "status": "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY",
        }

    def run(self, install: bool = True, timeout: int = 300) -> dict:
        return {
            "ok": False,
            "status": "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY",
            "execution_mode": "SIMULATION_ONLY",
            "real_windows_boot_verified": False,
        }
