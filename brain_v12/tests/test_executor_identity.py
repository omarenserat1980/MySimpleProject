import unittest

from brain_v12.brain.executor_identity import (
    ARKAN_DEVICE_ID,
    ARKAN_EXECUTOR_ID,
    ARKAN_RUNNER_ID,
    configured_executor,
    identity,
    matches_agent,
)


class ExecutorIdentityTests(unittest.TestCase):
    def test_identity_is_stable_and_hostname_is_alias(self):
        item = identity()
        self.assertEqual(item["executor_id"], ARKAN_EXECUTOR_ID)
        self.assertEqual(item["runner_id"], ARKAN_RUNNER_ID)
        self.assertEqual(item["device_id"], ARKAN_DEVICE_ID)
        self.assertEqual(item["host_alias"], "arkan")
        self.assertEqual(item["identity_policy"], "STABLE_IDENTITY_HOSTNAME_ALIAS_ONLY")

    def test_stable_ids_select_agent_even_without_hostname(self):
        agent = {
            "agent_id": "renamed-host",
            "executor_id": ARKAN_EXECUTOR_ID,
            "runner_id": ARKAN_RUNNER_ID,
            "device_id": ARKAN_DEVICE_ID,
            "online": True,
        }
        self.assertTrue(matches_agent(agent))

    def test_legacy_hostname_remains_compatibility_alias(self):
        self.assertTrue(matches_agent({"agent_id": "arkan", "online": True}))

    def test_arbitrary_agent_is_not_selected(self):
        self.assertFalse(matches_agent({"agent_id": "other-host", "online": True}))


if __name__ == "__main__":
    unittest.main()
