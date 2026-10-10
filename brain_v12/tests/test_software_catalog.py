import unittest

from brain_v12.brain.software_catalog import build_readiness, get_catalog


class SoftwareCatalogTests(unittest.TestCase):
    def test_catalog_is_explicitly_desired_state_not_live_inventory(self):
        catalog = get_catalog()
        self.assertFalse(catalog["execution_enabled"])
        self.assertGreaterEqual(catalog["total"] if "total" in catalog else len(catalog["items"]), 8)
        windows = next(item for item in catalog["items"] if item["software_id"] == "windows-server-2025")
        self.assertEqual(windows["target_state"], "running")
        self.assertEqual(windows["rollout_phase"], "planned")
        self.assertFalse(windows["install_allowed"])
        self.assertIn("guest-boot-proof", windows["verification_gates"])

    def test_readiness_does_not_claim_unregistered_items_are_ready(self):
        result = build_readiness([])
        self.assertEqual(result["ready_count"], 0)
        self.assertFalse(result["execution_enabled"])
        self.assertTrue(all(item["inventory_state"] == "not-registered" for item in result["items"]))

    def test_ready_requires_matching_state_and_verification(self):
        result = build_readiness([{
            "software_id": "python-runtime",
            "runtime_state": "installed",
            "verification_state": "verified",
        }])
        python = next(item for item in result["items"] if item["software_id"] == "python-runtime")
        self.assertTrue(python["ready"])
        self.assertFalse(python["install_allowed"])

        unverified = build_readiness([{
            "software_id": "git",
            "runtime_state": "installed",
            "verification_state": "unverified",
        }])
        git = next(item for item in unverified["items"] if item["software_id"] == "git")
        self.assertFalse(git["ready"])


if __name__ == "__main__":
    unittest.main()
