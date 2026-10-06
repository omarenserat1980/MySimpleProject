import hashlib
import os
import unittest

from brain_v12.brain import industrial_clients


class IndustrialClientRequestTests(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get("BRAIN_INDUSTRIAL_CLIENT_KEY_SHA256")
        os.environ["BRAIN_INDUSTRIAL_CLIENT_KEY_SHA256"] = hashlib.sha256(
            b"test-client-key"
        ).hexdigest()

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BRAIN_INDUSTRIAL_CLIENT_KEY_SHA256", None)
        else:
            os.environ["BRAIN_INDUSTRIAL_CLIENT_KEY_SHA256"] = self.old

    def test_auth_and_fixed_mapping(self):
        self.assertTrue(
            industrial_clients.authenticate(
                industrial_clients.INDUSTRIAL_CLIENT_ID, "test-client-key"
            )
        )
        result = industrial_clients.build_request(
            industrial_clients.INDUSTRIAL_CLIENT_ID,
            industrial_clients.ALLOWED_REQUEST,
            "arkan",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["workflow"], industrial_clients.PRIMARY_WORKFLOW
        )
        self.assertEqual(
            result["execution_policy"], "EXISTING_PRIMARY_PIPELINE"
        )

    def test_arbitrary_target_is_rejected(self):
        result = industrial_clients.build_request(
            industrial_clients.INDUSTRIAL_CLIENT_ID,
            industrial_clients.ALLOWED_REQUEST,
            "other-device",
        )
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main()
