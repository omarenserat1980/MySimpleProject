import os
import tempfile
import unittest
from unittest.mock import patch

from brain_v12.brain.cloud_direct_action_executor import _verify_contract


class CloudDirectActionExecutorTests(unittest.TestCase):
    def base_contract(self):
        return {
            "status": "VERIFIED",
            "capability": "windows-server-2025-real-boot",
            "executor": "windows-real-boot-qemu",
            "source_commit": "a" * 40,
            "task_id": "windows-server-2025-real-boot",
            "expires_at": 4102444800,
            "authority_signature": "invalid",
            "authority_signature_algorithm": "Ed25519",
        }

    def test_unknown_action_is_rejected_before_execution(self):
        c = self.base_contract()
        with patch.dict(os.environ, {"BRAIN_AUTHORITY_PUBLIC_KEY_B64": "unused"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "ACTION_NOT_ALLOWLISTED"):
                _verify_contract(c, "a" * 40, "shell")

    def test_commit_binding_is_enforced(self):
        c = self.base_contract()
        with self.assertRaisesRegex(RuntimeError, "ACTION_CONTRACT_SOURCE_COMMIT_MISMATCH"):
            _verify_contract(c, "b" * 40, "integration_gate")


if __name__ == "__main__":
    unittest.main()
