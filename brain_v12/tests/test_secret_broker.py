import unittest
from brain_v12.brain.permissions import PermissionGate
from brain_v12.brain.secret_broker import SecretBroker

class SecretBrokerTests(unittest.TestCase):
    def test_denies_without_credentials_permission(self):
        with self.assertRaises(PermissionError):
            SecretBroker({"CLOUDFLARE_API_TOKEN": "secret"}).status(["CLOUDFLARE_API_TOKEN"])

    def test_reports_presence_without_exposing_value(self):
        gate = PermissionGate(); gate.grant("credentials")
        result = SecretBroker({"CLOUDFLARE_API_TOKEN": "secret"}, gate).status(["CLOUDFLARE_API_TOKEN"])[0]
        self.assertTrue(result.configured)
        self.assertEqual(len(result.fingerprint), 12)
        self.assertNotEqual(result.fingerprint, "secret")

    def test_missing_secret_is_detected(self):
        gate = PermissionGate(); gate.grant("credentials")
        with self.assertRaisesRegex(RuntimeError, "PAYTABS_SERVER_KEY"):
            SecretBroker({}, gate).require(["PAYTABS_SERVER_KEY"])

if __name__ == "__main__":
    unittest.main()
