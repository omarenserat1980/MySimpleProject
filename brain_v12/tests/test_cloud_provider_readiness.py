import unittest

from brain_v12.brain.cloud_provider_readiness import discover_provider_configuration


class CloudProviderReadinessTests(unittest.TestCase):
    def test_no_credentials_fails_closed(self):
        result = discover_provider_configuration({})
        self.assertEqual(result["status"], "NO_AUTHORIZED_PROVIDER")
        self.assertEqual(result["configured_provider_count"], 0)
        self.assertFalse(result["provider_api_checked"])
        self.assertFalse(result["zero_cost_verified"])
        self.assertFalse(result["physical_node_verified"])
        self.assertFalse(result["provisioning_allowed"])

    def test_configured_credentials_are_not_treated_as_verified(self):
        result = discover_provider_configuration({
            "AZURE_SUBSCRIPTION_ID": "subscription-placeholder",
            "AZURE_TENANT_ID": "tenant-placeholder",
            "AZURE_CLIENT_ID": "client-placeholder",
            "AZURE_CLIENT_SECRET": "do-not-return-this",
        })
        azure = next(item for item in result["providers"] if item["provider"] == "azure")
        self.assertEqual(azure["status"], "CONFIGURED_UNVERIFIED")
        self.assertFalse(azure["authenticated"])
        self.assertFalse(azure["free_capacity_verified"])
        self.assertFalse(azure["provisioning_allowed"])
        self.assertNotIn("do-not-return-this", repr(result))
        self.assertFalse(azure["secret_values_exposed"])

    def test_partial_provider_configuration_reports_missing_names_only(self):
        result = discover_provider_configuration({"AWS_ACCESS_KEY_ID": "example"})
        aws = next(item for item in result["providers"] if item["provider"] == "aws")
        self.assertEqual(aws["status"], "NOT_CONFIGURED")
        self.assertEqual(aws["missing_variables"], ["AWS_SECRET_ACCESS_KEY"])
        self.assertFalse(aws["provisioning_allowed"])


if __name__ == "__main__":
    unittest.main()
