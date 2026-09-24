import os
import unittest

from brain_v12.brain.secret_control import SecretControlPlane


class SecretControlPlaneTests(unittest.TestCase):
    def test_never_returns_secret_values(self):
        env = {
            "RENDER_API_KEY": "render-secret-value",
            "RENDER_OWNER_ID": "owner-123",
            "OPENAI_API_KEY": "openai-secret-value",
        }
        status = SecretControlPlane(env).status()
        raw = str(status)
        self.assertNotIn("render-secret-value", raw)
        self.assertNotIn("openai-secret-value", raw)
        self.assertFalse(any(x.get("value_exposed") for x in status["secrets"]))
        self.assertEqual(status["missing"], [])

    def test_missing_secret_is_reported_without_value(self):
        env = {"RENDER_SERVICE_ID": "srv-test"}
        status = SecretControlPlane(env).status()
        self.assertEqual(
            set(status["missing"]),
            {"RENDER_API_KEY", "RENDER_OWNER_ID", "OPENAI_API_KEY"},
        )

    def test_plan_requires_external_connector_for_remote_write(self):
        plan = SecretControlPlane({}).plan()
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["status"], "READY")
        self.assertTrue(all(x["write_requires_explicit_approval"] for x in plan["secrets"]))
        self.assertFalse(any(x["value_returned"] for x in plan["secrets"]))


if __name__ == "__main__":
    unittest.main()
