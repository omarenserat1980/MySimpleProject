import os
import tempfile
import unittest
from unittest.mock import patch


class FabricTrustGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {"BRAIN_FABRIC_STATE_DIR": self.temp.name},
        )
        self.env.start()

        from cloud import brain_fabric
        self.fabric = brain_fabric

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_new_node_is_untrusted_and_inactive(self):
        node = self.fabric.register_node(
            "test-node", capabilities=["test-only"]
        )
        self.assertEqual(node["state"], "UNTRUSTED_INACTIVE")
        self.assertIs(node["trusted"], False)
        self.assertIs(node["active"], False)
        self.assertIs(node["identity_verified"], False)
        self.assertIs(node["manual_approval"], False)

    def test_heartbeat_cannot_promote_node(self):
        self.fabric.register_node("test-node")
        node = self.fabric.heartbeat(
            "test-node", state="READY", jobs_running=0
        )
        self.assertEqual(node["state"], "UNTRUSTED_INACTIVE")

    def test_untrusted_node_cannot_be_selected(self):
        self.fabric.register_node(
            "test-node", capabilities=["test-only"]
        )
        with self.assertRaisesRegex(
            RuntimeError, "NO_ELIGIBLE_BRAIN_FABRIC_NODE"
        ):
            self.fabric.choose_node(["test-only"])

    def test_ready_state_alone_is_not_enough(self):
        node = self.fabric.register_node(
            "test-node", capabilities=["test-only"]
        )
        node.update(
            state="READY",
            last_heartbeat=self.fabric._now(),
        )
        self.assertFalse(
            self.fabric._eligible(node, {"test-only"})
        )


    def test_update_node_cannot_grant_trust_fields(self):
        self.fabric.register_node(
            "test-node", capabilities=["test-only"]
        )
        with self.assertRaises(ValueError):
            self.fabric.update_node(
                "test-node",
                trusted=True,
            )
        with self.assertRaises(ValueError):
            self.fabric.update_node(
                "test-node",
                identity_verified=True,
            )
        with self.assertRaises(ValueError):
            self.fabric.update_node(
                "test-node",
                manual_approval=True,
            )
        with self.assertRaises(ValueError):
            self.fabric.update_node(
                "test-node",
                active=True,
            )


if __name__ == "__main__":
    unittest.main()
