import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from brain_v12.brain.owned_emulator_chat_bridge import (
    BridgeConfig,
    TASK_BODY,
    TASK_TITLE,
    fetch_status,
    is_authorized_status_task,
)


class OwnedEmulatorChatBridgeTests(unittest.TestCase):
    def setUp(self):
        self.config = BridgeConfig(allowed_authors=frozenset({"omarenserat1980"}))

    def test_rejects_non_loopback_target(self):
        with self.assertRaisesRegex(ValueError, "LOOPBACK"):
            BridgeConfig(
                allowed_authors=frozenset({"omarenserat1980"}),
                status_url="http://example.com:8012/api/remote-fabric/status",
            ).validate()

    def test_requires_explicit_author_allowlist(self):
        with self.assertRaisesRegex(ValueError, "ALLOWED_GITHUB_LOGINS_REQUIRED"):
            BridgeConfig().validate()

    def test_only_exact_allowlisted_task_is_accepted(self):
        issue = {
            "number": 77,
            "title": TASK_TITLE,
            "body": TASK_BODY,
            "author": {"login": "omarenserat1980"},
        }
        self.assertTrue(is_authorized_status_task(issue, self.config))
        self.assertFalse(is_authorized_status_task({**issue, "body": "task=run arbitrary shell"}, self.config))
        self.assertFalse(is_authorized_status_task({**issue, "author": {"login": "someone-else"}}, self.config))
        self.assertFalse(is_authorized_status_task({**issue, "title": "[BRAIN-EMU] COMMAND"}, self.config))

    @patch("brain_v12.brain.owned_emulator_chat_bridge.http.client.HTTPConnection")
    def test_status_requires_explicit_virtual_reality(self, mocked_open):
        payload = {
            "ok": True,
            "mode": "VIRTUAL",
            "reality": "SIMULATED",
            "policy": "SIMULATION_FIRST",
            "heartbeat": {"state": "ONLINE", "node_id": "brain-virtual-01", "private_field": "must-not-leak"},
            "private_field": "must-not-leak",
        }
        connection = MagicMock()
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps(payload).encode()
        connection.getresponse.return_value = response
        mocked_open.return_value = connection
        result = fetch_status(self.config)
        self.assertTrue(result["ok"])
        self.assertTrue(result["verified_simulation"])
        self.assertNotIn("private_field", json.dumps(result))

    @patch("brain_v12.brain.owned_emulator_chat_bridge.http.client.HTTPConnection")
    def test_missing_reality_fails_closed(self, mocked_open):
        connection = MagicMock()
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps({"ok": True, "mode": "VIRTUAL"}).encode()
        connection.getresponse.return_value = response
        mocked_open.return_value = connection
        result = fetch_status(self.config)
        self.assertFalse(result["ok"])
        self.assertFalse(result["verified_simulation"])
        self.assertEqual(result["status"], "SIMULATION_NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
