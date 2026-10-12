import unittest

from brain_v12.tools.windows_server_install_plan import build_plan, verify_media_provenance


GOOD_HASH = "a" * 64


class WindowsServerInstallPlanTests(unittest.TestCase):
    def test_requires_https_microsoft_source_and_trusted_matching_hash(self):
        self.assertTrue(verify_media_provenance("https://go.microsoft.com/fwlink?id=1", GOOD_HASH, GOOD_HASH)["passed"])
        self.assertFalse(verify_media_provenance("http://go.microsoft.com/fwlink?id=1", GOOD_HASH, GOOD_HASH)["passed"])
        self.assertFalse(verify_media_provenance("https://example.invalid/server.iso", GOOD_HASH, GOOD_HASH)["passed"])
        self.assertFalse(verify_media_provenance("https://go.microsoft.com/fwlink?id=1", GOOD_HASH, "b" * 64)["passed"])
        self.assertFalse(verify_media_provenance("https://go.microsoft.com/fwlink?id=1", GOOD_HASH, None)["passed"])

    def valid_plan(self, **overrides):
        values = dict(
            source_url="https://go.microsoft.com/fwlink?id=1",
            actual_sha256=GOOD_HASH,
            trusted_sha256=GOOD_HASH,
            iso_size_bytes=6_000_000_000,
            disk_size_gib=100,
            backend="qemu-kvm",
            backend_available=True,
            target_is_virtual_disk=True,
            target_unambiguous=True,
            destructive_authorized=True,
        )
        values.update(overrides)
        return build_plan(**values)

    def test_valid_plan_is_not_boot_evidence_and_has_gpt_layout(self):
        report = self.valid_plan()
        self.assertEqual(report["status"], "INSTALLATION_PLAN_READY")
        self.assertEqual(report["boot_status"], "NOT_TESTED")
        self.assertFalse(report["partition_plan"]["executed"])
        self.assertEqual(report["partition_plan"]["scheme"], "GPT")
        self.assertEqual([p["type"] for p in report["partition_plan"]["partitions"]],
                         ["EFI", "MSR", "OS", "Recovery"])

    def test_physical_or_ambiguous_disk_blocks(self):
        self.assertEqual(self.valid_plan(target_is_virtual_disk=False)["status"], "BLOCKED")
        self.assertEqual(self.valid_plan(target_unambiguous=False)["status"], "BLOCKED")

    def test_missing_explicit_destructive_authorization_blocks(self):
        report = self.valid_plan(destructive_authorized=False)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertIn("destructive_authorization", report["blockers"])

    def test_insufficient_disk_or_backend_blocks(self):
        self.assertEqual(self.valid_plan(disk_size_gib=32)["status"], "BLOCKED")
        self.assertEqual(self.valid_plan(backend_available=False)["status"], "BLOCKED")

    def test_plan_never_claims_install_or_boot(self):
        report = self.valid_plan()
        self.assertNotEqual(report["status"], "WINDOWS_FIRST_BOOT_VERIFIED")
        self.assertEqual(report["boot_status"], "NOT_TESTED")


if __name__ == "__main__":
    unittest.main()
