import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from brain_v12.tools.windows_server_iso_preflight import inspect_iso


class WindowsServerIsoPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.iso = Path(self.temp.name) / "server.iso"
        self.iso.write_bytes(b"sample-iso")

    def tearDown(self):
        self.temp.cleanup()

    @patch("brain_v12.tools.windows_server_iso_preflight.shutil.which", return_value=None)
    def test_missing_xorriso_fails_closed(self, _which):
        report = inspect_iso(self.iso)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["boot_status"], "NOT_TESTED")
        self.assertIn("sha256", report)

    @patch("brain_v12.tools.windows_server_iso_preflight.shutil.which", return_value="/usr/bin/xorriso")
    @patch("brain_v12.tools.windows_server_iso_preflight.subprocess.run")
    def test_required_uefi_and_setup_files_are_required(self, run, _which):
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="xorriso 1.5.6", stderr=""),
            SimpleNamespace(returncode=0, stdout=(
                "/EFI/BOOT/BOOTX64.EFI\n/sources/boot.wim\n/sources/install.wim\n"
            ), stderr=""),
        ]
        report = inspect_iso(self.iso)
        self.assertEqual(report["status"], "ISO_STRUCTURE_VALIDATED")
        self.assertEqual(report["boot_status"], "NOT_TESTED")
        self.assertTrue(report["checks"]["uefi_and_setup_files"]["passed"])

    @patch("brain_v12.tools.windows_server_iso_preflight.shutil.which", return_value="/usr/bin/xorriso")
    @patch("brain_v12.tools.windows_server_iso_preflight.subprocess.run")
    def test_missing_efi_boot_file_blocks_validation(self, run, _which):
        run.side_effect = [
            SimpleNamespace(returncode=0, stdout="xorriso 1.5.6", stderr=""),
            SimpleNamespace(returncode=0, stdout="/sources/boot.wim\n/sources/install.esd\n", stderr=""),
        ]
        report = inspect_iso(self.iso)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["checks"]["uefi_and_setup_files"]["required_files_missing"],
                         ["efi/boot/bootx64.efi"])

    def test_empty_or_missing_iso_fails_closed(self):
        missing = Path(self.temp.name) / "missing.iso"
        report = inspect_iso(missing)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse(report["checks"]["iso_file"]["passed"])


if __name__ == "__main__":
    unittest.main()
