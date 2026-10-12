import unittest

from brain_v12.brain.windows_cloud_secret_gate import check_windows_cloud_secret_readiness


class WindowsCloudSecretGateTests(unittest.TestCase):
    def test_ready_when_required_guest_configuration_is_present(self):
        env = {
            "BRAIN_FABRIC_URL": "https://fabric.example",
            "BRAIN_WINDOWS_NODE_ID": "windows-cloud-01",
            "BRAIN_ENROLLMENT_TOKEN": "enrollment-secret",
            "BRAIN_CONTROL_TOKEN": "control-secret",
        }
        result = check_windows_cloud_secret_readiness(env)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["missing"], [])
        raw = str(result)
        self.assertNotIn("enrollment-secret", raw)
        self.assertNotIn("control-secret", raw)
        self.assertTrue(all(not x.get("value_exposed") for x in result["checks"]))

    def test_control_key_is_supported_as_legacy_alias(self):
        env = {
            "BRAIN_FABRIC_URL": "http://fabric.internal:8000",
            "BRAIN_WINDOWS_NODE_ID": "windows-cloud-01",
            "BRAIN_ENROLLMENT_TOKEN": "enrollment-secret",
            "BRAIN_CONTROL_KEY": "control-secret",
        }
        result = check_windows_cloud_secret_readiness(env)
        self.assertTrue(result["ok"])
        self.assertEqual(
            next(x for x in result["checks"] if x["name"] == "control_auth")["source"],
            "BRAIN_CONTROL_KEY",
        )

    def test_missing_configuration_fails_closed(self):
        result = check_windows_cloud_secret_readiness({})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(
            set(result["missing"]),
            {"fabric_url", "windows_node_id", "enrollment_token", "control_auth"},
        )

    def test_secret_values_never_appear_in_output(self):
        env = {
            "BRAIN_FABRIC_URL": "https://fabric.example",
            "BRAIN_WINDOWS_NODE_ID": "windows-cloud-01",
            "BRAIN_ENROLLMENT_TOKEN": "SUPER-SECRET-ENROLLMENT",
            "BRAIN_CONTROL_TOKEN": "SUPER-SECRET-CONTROL",
        }
        result = check_windows_cloud_secret_readiness(env)
        serialized = repr(result)
        self.assertNotIn("SUPER-SECRET-ENROLLMENT", serialized)
        self.assertNotIn("SUPER-SECRET-CONTROL", serialized)


if __name__ == "__main__":
    unittest.main()
