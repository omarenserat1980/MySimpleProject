import os
import tempfile
import unittest
from unittest.mock import patch

from brain_v12.brain.device_bridge import DeviceBridge


class DeviceBridgeBootstrapTests(unittest.TestCase):
    def test_local_trust_root_enables_bridge_without_enable_env(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("test-agent-key")
            key_file = f.name
        try:
            with patch.dict(
                os.environ,
                {
                    "BRAIN_AGENT_KEY_FILE": key_file,
                    "BRAIN_ENABLE_DEVICE_BRIDGE": "",
                    "BRAIN_AGENT_KEY": "",
                    "BRAIN_AGENT_KEY_SHA256": "",
                    "BRAIN_AGENT_KEYS_JSON": "",
                    "BRAIN_EMULATOR_KEY": "",
                },
                clear=False,
            ):
                bridge = DeviceBridge(store=None)
                self.assertTrue(bridge.configured())
                self.assertTrue(bridge.enabled())
                self.assertTrue(bridge.authenticate("test-agent-key"))
        finally:
            os.unlink(key_file)

    def test_missing_local_trust_root_keeps_bridge_disabled(self):
        missing = os.path.join(tempfile.gettempdir(), "brain-missing-agent-key-do-not-create")
        with patch.dict(
            os.environ,
            {
                "BRAIN_AGENT_KEY_FILE": missing,
                "BRAIN_ENABLE_DEVICE_BRIDGE": "",
                "BRAIN_AGENT_KEY": "",
                "BRAIN_AGENT_KEY_SHA256": "",
                "BRAIN_AGENT_KEYS_JSON": "",
                "BRAIN_EMULATOR_KEY": "",
            },
            clear=False,
        ):
            bridge = DeviceBridge(store=None)
            self.assertFalse(bridge.configured())
            self.assertFalse(bridge.enabled())


if __name__ == "__main__":
    unittest.main()
