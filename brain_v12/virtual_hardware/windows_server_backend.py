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
        """Materialize and verify Microsoft media on this remote executor."""
        if self.iso_path and Path(self.iso_path).is_file():
            return {"ok": True, "status": "LOCAL_ISO_PRESENT", "path": self.iso_path}
        if not self.iso_url:
            raise ValueError("ISO_PATH_OR_OFFICIAL_URL_REQUIRED")
        if not self.iso_sha256:
            raise ValueError("ISO_SHA256_REQUIRED")
        cache_dir = Path(self.iso_cache_dir).expanduser()
        destination = Path(self.iso_path).expanduser() if self.iso_path else (
            cache_dir / "WindowsServer2025.iso"
        )
        result = download_official_windows_iso(
            self.iso_url, destination, expected_sha256=self.iso_sha256
        )
        self.iso_path = str(destination)
        return result

    def command(self, install: bool = True) -> list[str]:
        if not self.disk_path:
            raise ValueError("DISK_PATH_REQUIRED")
        cmd = [
            self.qemu_binary, "-machine", self.machine, "-m", self.memory,
            "-drive", "if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd",
            "-smp", str(self.cpus), "-drive", f"file={self.disk_path},format=qcow2,if=virtio",
            "-netdev", "user,id=net0", "-device", "virtio-net-pci,netdev=net0",
            "-display", "none", "-serial", "stdio",
        ]
        if install:
            if not self.iso_path:
                raise ValueError("ISO_PATH_REQUIRED")
            cmd += ["-cdrom", self.iso_path, "-boot", "order=d"]
        return cmd

    def inspect(self) -> dict:
        return {
            "ok": True,
            "backend": "qemu-system-x86_64",
            "available": self.available(),
            "binary": shutil.which(self.qemu_binary),
            "memory": self.memory,
            "cpus": self.cpus,
            "machine": self.machine,
            "disk": self.disk_path,
            "iso": self.iso_path,
            "iso_url_configured": bool(self.iso_url),
            "iso_sha256_configured": bool(self.iso_sha256),
            "iso_source_policy": "https-microsoft-hosts-only",
        }

    def run(self, install: bool = True, timeout: int = 300) -> dict:
        if not self.available():
            return {"ok": False, "status": "QEMU_NOT_AVAILABLE", "inspection": self.inspect()}
        media = None
        if install:
            try:
                media = self.prepare_iso()
            except (OSError, RuntimeError, ValueError) as exc:
                # Helper errors are deliberately token-free and do not expose
                # the direct download URL.
                return {
                    "ok": False,
                    "status": "WINDOWS_MEDIA_PREPARATION_FAILED",
                    "reason": str(exc),
                    "inspection": self.inspect(),
                }
        cmd = self.command(install)
        try:
            p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False, "status": "QEMU_TIMEOUT",
                "stdout": exc.stdout or "", "stderr": exc.stderr or "",
                "command": cmd, "media": media,
            }
        return {
            "ok": p.returncode == 0,
            "status": "QEMU_EXITED" if p.returncode == 0 else "QEMU_FAILED",
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "command": cmd,
            "media": media,
        }
