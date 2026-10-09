"""Focused unit tests for DeviceBridge key configuration and authentication."""
import os
import tempfile
import unittest
from unittest.mock import patch

from brain_v12.brain.device_bridge import DeviceBridge


class DeviceBridgeAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bridge = DeviceBridge(store=object())

    def _clear_auth_env(self):
        return patch.dict(os.environ, {
            "BRAIN_AGENT_KEY": "",
            "BRAIN_AGENT_KEY_SHA256": "",
            "BRAIN_EMULATOR_KEY": "",
            "BRAIN_EMULATOR_AGENT_KEY": "",
            "BRAIN_AGENT_KEY_FILE": os.path.join(self.temp.name, "missing.key"),
            "V12_AGENT_KEY_FILE": "",
            "BRAIN_ENABLE_DEVICE_BRIDGE": "1",
        }, clear=False)

    def test_empty_and_whitespace_environment_keys_are_not_configured(self):
        with self._clear_auth_env(), patch.dict(os.environ, {
            "BRAIN_AGENT_KEY": "   ",
            "BRAIN_AGENT_KEY_SHA256": "\t ",
            "BRAIN_EMULATOR_KEY": " ",
            "BRAIN_EMULATOR_AGENT_KEY": "\n",
        }):
            self.assertFalse(self.bridge.configured())
            self.assertEqual(self.bridge.auth_mode(), "NOT_CONFIGURED")
            self.assertFalse(self.bridge.authenticate("anything"))

    def test_direct_key_authentication_and_wrong_key_rejection(self):
        with self._clear_auth_env(), patch.dict(os.environ, {"BRAIN_AGENT_KEY": "secret-value"}):
            self.assertTrue(self.bridge.configured())
            self.assertEqual(self.bridge.auth_mode(), "DIRECT_KEY")
            self.assertTrue(self.bridge.authenticate("secret-value"))
            self.assertFalse(self.bridge.authenticate("wrong-value"))

    def test_emulator_agent_key_is_recognized_and_accepted(self):
        with self._clear_auth_env(), patch.dict(os.environ, {"BRAIN_EMULATOR_AGENT_KEY": "emulator-secret"}):
            self.assertEqual(self.bridge.auth_mode(), "BRAIN_EMULATOR_AGENT_KEY")
            self.assertTrue(self.bridge.authenticate("emulator-secret"))

    def test_local_key_file_authentication(self):
        key_path = os.path.join(self.temp.name, "agent.key")
        with open(key_path, "w", encoding="utf-8") as handle:
            handle.write("file-secret\n")
        with self._clear_auth_env(), patch.dict(os.environ, {"BRAIN_AGENT_KEY_FILE": key_path}):
            self.assertTrue(self.bridge.configured())
            self.assertEqual(self.bridge.auth_mode(), "LOCAL_KEY_FILE")
            self.assertTrue(self.bridge.authenticate("file-secret"))
            self.assertFalse(self.bridge.authenticate("bad-secret"))

    def test_sha256_key_authentication(self):
        import hashlib
        digest = hashlib.sha256(b"hashed-secret").hexdigest()
        with self._clear_auth_env(), patch.dict(os.environ, {"BRAIN_AGENT_KEY_SHA256": digest}):
            self.assertTrue(self.bridge.configured())
            self.assertEqual(self.bridge.auth_mode(), "SHA256_KEY")
            self.assertTrue(self.bridge.authenticate("hashed-secret"))
            self.assertFalse(self.bridge.authenticate("wrong-secret"))

    def test_disabled_bridge_rejects_even_correct_key(self):
        with self._clear_auth_env(), patch.dict(os.environ, {
            "BRAIN_AGENT_KEY": "secret-value",
            "BRAIN_ENABLE_DEVICE_BRIDGE": "0",
        }):
            self.assertFalse(self.bridge.enabled())
            self.assertFalse(self.bridge.authenticate("secret-value"))


if __name__ == "__main__":
    unittest.main()
