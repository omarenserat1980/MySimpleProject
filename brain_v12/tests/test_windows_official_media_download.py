import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.tools.windows_official_media_download import download_official_media


class FakeResponse:
    def __init__(self, body, status=200, headers=None, url="https://download.microsoft.com/server.iso"):
        self.body = body
        self.status = status
        self.headers = headers or {"Content-Length": str(len(body))}
        self.url = url
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        if size < 0:
            size = len(self.body)
        part = self.body[self.offset:self.offset + size]
        self.offset += len(part)
        return part

    def getcode(self):
        return self.status

    def geturl(self):
        return self.url


class FakeOpener:
    def __init__(self, response):
        self.response = response

    def open(self, request, timeout=0):
        return self.response


class WindowsOfficialMediaDownloadTests(unittest.TestCase):
    def test_rejects_non_microsoft_or_non_https_source_before_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "server.iso"
            with self.assertRaises(ValueError):
                download_official_media("http://download.microsoft.com/server.iso", dest, "a" * 64)
            with self.assertRaises(ValueError):
                download_official_media("https://example.invalid/server.iso", dest, "a" * 64)
            self.assertFalse(dest.exists())

    def test_requires_trusted_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                download_official_media("https://download.microsoft.com/server.iso", Path(tmp) / "server.iso", "unknown")

    def test_download_promotes_only_after_checksum_match(self):
        body = b"official-media-sample"
        digest = hashlib.sha256(body).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "server.iso"
            response = FakeResponse(body)
            with patch("brain_v12.tools.windows_official_media_download.urllib.request.build_opener",
                       return_value=FakeOpener(response)):
                report = download_official_media("https://go.microsoft.com/fwlink?id=1", dest, digest)
            self.assertEqual(report["status"], "OFFICIAL_MEDIA_VERIFIED")
            self.assertEqual(dest.read_bytes(), body)
            self.assertFalse(dest.with_name(dest.name + ".part").exists())

    def test_checksum_mismatch_does_not_promote_partial_file(self):
        body = b"not-the-expected-media"
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "server.iso"
            response = FakeResponse(body)
            with patch("brain_v12.tools.windows_official_media_download.urllib.request.build_opener",
                       return_value=FakeOpener(response)):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    download_official_media("https://go.microsoft.com/fwlink?id=1", dest, "0" * 64)
            self.assertFalse(dest.exists())
            self.assertTrue(dest.with_name(dest.name + ".part").exists())

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "server.iso"
            dest.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                download_official_media("https://download.microsoft.com/server.iso", dest, "a" * 64)
            self.assertEqual(dest.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
