import unittest
from unittest.mock import patch

from brain_v12.brain import brain_cloud_provider_api


class BrainCloudProviderApiTests(unittest.TestCase):
    def test_status_reports_no_verified_capacity_without_fabricating_worker(self):
        with patch.object(brain_cloud_provider_api, "require_control_key"):
            result = brain_cloud_provider_api.provider_status(object())
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "brain-cloud")
        self.assertEqual(result["status"], "NO_VERIFIED_CAPACITY")
        self.assertEqual(result["capacity"]["worker_count"], 0)
        self.assertFalse(result["provisioning_supported"])

    def test_readiness_fails_closed_when_provider_is_not_configured(self):
        with patch.object(brain_cloud_provider_api, "require_control_key"), patch.object(
            brain_cloud_provider_api,
            "discover_provider_configuration",
            return_value={"configured_provider_count": 0, "status": "NO_AUTHORIZED_PROVIDER"},
        ):
            result = brain_cloud_provider_api.provider_readiness(object())
        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("NO_VERIFIED_REAL_WORKER", result["blockers"])
        self.assertIn("PROVIDER_SPECIFIC_PROVISIONING_ADAPTER_NOT_IMPLEMENTED", result["blockers"])
        self.assertFalse(result["provisioning_allowed"])
        self.assertFalse(result["secret_values_exposed"])

    def test_status_requires_control_authentication(self):
        with patch.object(
            brain_cloud_provider_api,
            "require_control_key",
            side_effect=PermissionError("CONTROL_AUTH_REQUIRED"),
        ):
            with self.assertRaises(PermissionError):
                brain_cloud_provider_api.provider_status(object())


if __name__ == "__main__":
    unittest.main()
