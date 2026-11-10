import unittest

from brain_v12.brain.device_heartbeat_auth import (
    HeartbeatAuthorizationError,
    authorize_heartbeat_identity,
)


class HeartbeatAuthorizationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.valid = {"realme-01": "realme-test-key", "redmi3-01": "redmi-test-key"}
        self.calls = []

        def authenticate(key, agent_id):
            self.calls.append((key, agent_id))
            return self.valid.get(agent_id) == key

        self.authenticate = authenticate

    def test_per_agent_mode_requires_explicit_identity_before_authentication(self):
        with self.assertRaises(HeartbeatAuthorizationError) as raised:
            authorize_heartbeat_identity("", "", "realme-test-key", True, self.authenticate)
        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "DEVICE_AGENT_ID_REQUIRED")
        self.assertEqual(self.calls, [])

    def test_valid_identity_and_key_are_accepted(self):
        agent_id = authorize_heartbeat_identity(
            " realme-01 ", "", "realme-test-key", True, self.authenticate
        )
        self.assertEqual(agent_id, "realme-01")
        self.assertEqual(self.calls, [("realme-test-key", "realme-01")])

    def test_wrong_agent_key_is_rejected(self):
        with self.assertRaises(HeartbeatAuthorizationError) as raised:
            authorize_heartbeat_identity(
                "realme-01", "", "redmi-test-key", True, self.authenticate
            )
        self.assertEqual(raised.exception.detail, "UNAUTHORIZED_AGENT")

    def test_header_body_identity_mismatch_is_rejected_before_authentication(self):
        with self.assertRaises(HeartbeatAuthorizationError) as raised:
            authorize_heartbeat_identity(
                "realme-01", "redmi3-01", "realme-test-key", True, self.authenticate
            )
        self.assertEqual(raised.exception.detail, "DEVICE_AGENT_ID_MISMATCH")
        self.assertEqual(self.calls, [])

    def test_legacy_default_is_only_used_when_per_agent_mode_is_off(self):
        seen = []

        def legacy_authenticate(key, agent_id):
            seen.append((key, agent_id))
            return key == "legacy-test-key" and agent_id == "android-termux-v12"

        result = authorize_heartbeat_identity(
            "", "", "legacy-test-key", False, legacy_authenticate
        )
        self.assertEqual(result, "android-termux-v12")
        self.assertEqual(seen, [("legacy-test-key", "android-termux-v12")])

    def test_missing_identity_in_legacy_mode_still_requires_valid_key(self):
        with self.assertRaises(HeartbeatAuthorizationError) as raised:
            authorize_heartbeat_identity("", "", "wrong", False, self.authenticate)
        self.assertEqual(raised.exception.detail, "UNAUTHORIZED_AGENT")


if __name__ == "__main__":
    unittest.main()
