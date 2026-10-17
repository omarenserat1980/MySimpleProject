import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.virtual_hardware.windows_iso_fetch import (
    _validate_url,
    download_official_windows_iso,
)
from brain_v12.virtual_hardware.windows_server_backend import QemuWindowsBackend


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}
        self._read = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status

    def read(self, size=-1):
        if self._read:
            return b""
        self._read = True
        return self.body


class QemuWindowsBackendTests(unittest.TestCase):
    def test_real_qemu_command_is_disabled(self):
        b = QemuWindowsBackend(
            disk_path="/brain/windows.raw",
            iso_path="/brain/WindowsServer2025.iso",
        )
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            b.command(True)

    def test_backend_reports_simulation_only(self):
        result = QemuWindowsBackend().run()
        self.assertFalse(result["ok"])
        self.assertEqual(
            result["status"], "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        )
        self.assertEqual(result["execution_mode"], "SIMULATION_ONLY")
        self.assertFalse(result["real_windows_boot_verified"])

    def test_remote_iso_url_downloads_on_executor_and_verifies_hash(self):
        body = b"synthetic test media"
        digest = hashlib.sha256(body).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "WindowsServer2025.iso"
            with patch(
                "brain_v12.virtual_hardware.windows_iso_fetch.urllib.request.build_opener"
            ) as build_opener:
                build_opener.return_value.open.return_value = _FakeResponse(body)
                result = download_official_windows_iso(
                    "https://download.microsoft.com/example.iso",
                    destination,
                    expected_sha256=digest,
                )
            self.assertTrue(result["ok"])
            self.assertEqual(destination.read_bytes(), body)
            self.assertEqual(result["sha256"], digest)

    def test_non_microsoft_or_plain_http_url_is_rejected(self):
        for url in (
            "http://download.microsoft.com/example.iso",
            "https://example.org/example.iso",
            "https://microsoft.com.evil.example/example.iso",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    _validate_url(url)

    def test_remote_iso_requires_expected_hash(self):
        b = QemuWindowsBackend(
            disk_path="/brain/windows.raw",
            iso_url="https://download.microsoft.com/example.iso",
        )
        with self.assertRaisesRegex(
            RuntimeError, "WINDOWS_REAL_EXECUTION_DISABLED_SIMULATION_ONLY"
        ):
            b.prepare_iso()


if __name__ == "__main__":
    unittest.main()
