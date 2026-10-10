import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.software_registry import SoftwareRegistry


class SoftwareRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.registry = SoftwareRegistry(Path(self.tmp.name) / "software.db")

    def tearDown(self):
        self.tmp.cleanup()

    def metadata(self, **overrides):
        value = {
            "name": "Python",
            "category": "runtime",
            "version": "3.x",
            "source": "system inventory",
            "license": "PSF",
            "runtime_state": "planned",
            "permissions": ["read-only"],
        }
        value.update(overrides)
        return value

    def test_registration_is_not_verification_or_installation(self):
        item = self.registry.register("python", self.metadata())
        self.assertEqual(item["runtime_state"], "planned")
        self.assertEqual(item["verification_state"], "unverified")
        self.assertIsNone(item["evidence_ref"])
        self.assertFalse(self.registry.summary()["execution_enabled"])

    def test_invalid_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_SOFTWARE_ID"):
            self.registry.register("../python", self.metadata())

    def test_missing_required_metadata_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_LICENSE"):
            self.registry.register("python", self.metadata(license=" "))

    def test_observation_cannot_self_assert_verified(self):
        self.registry.register("python", self.metadata())
        with self.assertRaisesRegex(ValueError, "EVIDENCE_REFERENCE_REQUIRED"):
            self.registry.record_observation("python", "running", "unverified", " ")
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_VERIFICATION_REQUIRED"):
            self.registry.record_observation("python", "running", "verified", "ci://run/123")
        item = self.registry.record_observation(
            "python", "running", "unverified", "ci://run/123"
        )
        self.assertEqual(item["verification_state"], "unverified")
        self.assertEqual(item["evidence_ref"], "ci://run/123")

    def test_unknown_software_cannot_be_observed(self):
        with self.assertRaisesRegex(KeyError, "SOFTWARE_NOT_FOUND"):
            self.registry.record_observation("missing", "running", "verified", "ci://run/1")

    def test_list_filter_and_summary(self):
        self.registry.register("python", self.metadata())
        self.registry.register("dotnet", self.metadata(name=".NET", category="developer-tool"))
        self.assertEqual(len(self.registry.list(category="runtime")), 1)
        self.assertEqual(self.registry.summary()["total"], 2)
        self.assertEqual(self.registry.summary()["unverified"], 2)


if __name__ == "__main__":
    unittest.main()
