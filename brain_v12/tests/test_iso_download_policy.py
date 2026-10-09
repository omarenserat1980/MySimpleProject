import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.iso_download_policy import (
    allowed_hosts_from_env, validate_source_url, verify_file_integrity,
)
from brain_v12.brain.iso_download_store import DownloadError


class IsoDownloadPolicyTests(unittest.TestCase):
    def test_exact_host_allowlist_and_wildcard_rejection(self):
        self.assertEqual(allowed_hosts_from_env("download.example, CDN.EXAMPLE."),
                         frozenset({"download.example", "cdn.example"}))
        with self.assertRaisesRegex(DownloadError, "INVALID_SOURCE_POLICY"):
            allowed_hosts_from_env("*.example.test")

    def test_rejects_http_credentials_ports_unlisted_host_and_fragment(self):
        hosts = frozenset({"download.example.test"})
        urls = ["http://download.example.test/a", "https://user@download.example.test/a",
                "https://download.example.test:8443/a", "https://evil.example.test/a",
                "https://download.example.test/a#frag"]
        for url in urls:
            with self.subTest(url=url), self.assertRaisesRegex(DownloadError, "SOURCE_NOT_ALLOWED"):
                validate_source_url(url, allowed_hosts=hosts, resolve_dns=False)

    def test_rejects_private_dns_answers(self):
        with patch("brain_v12.brain.iso_download_policy.socket.getaddrinfo",
                   return_value=[(None, None, None, None, ("127.0.0.1", 443))]):
            with self.assertRaisesRegex(DownloadError, "SOURCE_NOT_ALLOWED"):
                validate_source_url("https://download.example.test/a",
                                    allowed_hosts=frozenset({"download.example.test"}))

    def test_dns_failure_is_fail_closed(self):
        with patch("brain_v12.brain.iso_download_policy.socket.getaddrinfo", side_effect=OSError()):
            with self.assertRaisesRegex(DownloadError, "SOURCE_DNS_FAILED"):
                validate_source_url("https://download.example.test/a",
                                    allowed_hosts=frozenset({"download.example.test"}))

    def test_digest_required_and_correctness_checked(self):
        payload = b"test fixture only"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.bin"
            path.write_bytes(payload)
            with self.assertRaisesRegex(DownloadError, "INTEGRITY_METADATA_REQUIRED"):
                verify_file_integrity(path, expected_size=len(payload), expected_sha256=None)
            self.assertTrue(verify_file_integrity(path, expected_size=len(payload),
                                                  expected_sha256=digest)["verified"])
            with self.assertRaisesRegex(DownloadError, "INTEGRITY_CHECK_FAILED"):
                verify_file_integrity(path, expected_size=len(payload) + 1, expected_sha256=digest)
            with self.assertRaisesRegex(DownloadError, "INTEGRITY_CHECK_FAILED"):
                verify_file_integrity(path, expected_size=len(payload), expected_sha256="0" * 64)

    def test_symlink_is_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.write_bytes(b"abc")
            link = root / "link"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(DownloadError, "INTEGRITY_CHECK_FAILED"):
                verify_file_integrity(link, expected_size=3,
                                      expected_sha256=hashlib.sha256(b"abc").hexdigest())


if __name__ == "__main__":
    unittest.main()
