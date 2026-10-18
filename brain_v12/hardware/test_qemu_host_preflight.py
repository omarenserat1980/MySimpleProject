"""Tests for read-only QEMU/KVM host preflight."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from brain_v12.hardware import qemu_host_preflight as preflight


class QemuHostPreflightTests(unittest.TestCase):
    def test_ready_is_host_capability_only_not_guest_boot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            meminfo = root / "meminfo"
            meminfo.write_text("MemTotal: 1000 kB\nMemAvailable: 512 kB\n", encoding="utf-8")
            kvm = root / "kvm"
            kvm.touch()
            firmware = root / "OVMF.fd"
            firmware.touch()
            def which(name):
                return f"/usr/bin/{name}"
            def run(args, **kwargs):
                return mock.Mock(returncode=0, stdout="QEMU version 9.0", stderr="")
            with mock.patch.object(preflight.shutil, "which", side_effect=which), \
                 mock.patch.object(preflight.subprocess, "run", side_effect=run):
                result = preflight.probe_host(
                    meminfo_path=str(meminfo), kvm_path=str(kvm),
                    ovmf_candidates=(str(firmware),),
                )
        self.assertEqual(result["status"], "HOST_PREFLIGHT_READY")
        self.assertTrue(all(result["checks"].values()))
        self.assertFalse(result["vm_started"])
        self.assertFalse(result["guest_boot_verified"])
        self.assertFalse(result["physical_hardware_verified"])

    def test_missing_tools_or_kvm_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            meminfo = Path(d) / "meminfo"
            meminfo.write_text("MemAvailable: 42 kB\n", encoding="utf-8")
            with mock.patch.object(preflight.shutil, "which", return_value=None):
                result = preflight.probe_host(
                    meminfo_path=str(meminfo), kvm_path=str(Path(d) / "missing"),
                    ovmf_candidates=(),
                )
        self.assertEqual(result["status"], "HOST_PREFLIGHT_BLOCKED")
        self.assertFalse(result["checks"]["qemu_system"])
        self.assertFalse(result["checks"]["kvm_device"])

    def test_version_timeout_is_bounded(self):
        with mock.patch.object(preflight.shutil, "which", return_value="/usr/bin/qemu"), \
             mock.patch.object(preflight.subprocess, "run", side_effect=preflight.subprocess.TimeoutExpired("qemu", 5)):
            result = preflight._version("qemu-system-x86_64")
        self.assertFalse(result["available"])
        self.assertEqual(result["error"], "TimeoutExpired")


if __name__ == "__main__":
    unittest.main()
