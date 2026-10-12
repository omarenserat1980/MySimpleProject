import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain_v12.brain.error_recovery_api import _fingerprint, _redact, _severity


class ErrorRecoveryUnitTests(unittest.TestCase):
    def test_redacts_key_value_secrets(self):
        result = _redact("token=abc123 and Bearer xyz987")
        self.assertNotIn("abc123", result)
        self.assertNotIn("xyz987", result)

    def test_redacts_sensitive_dict_keys(self):
        result = _redact({"api_key": "abc", "safe": "ok"})
        self.assertEqual(result["api_key"], "[REDACTED]")
        self.assertEqual(result["safe"], "ok")

    def test_fingerprint_is_stable_and_source_scoped(self):
        self.assertEqual(_fingerprint("github-brain", "Build failed", {"code": "E1"}),
                         _fingerprint("github-brain", "Build failed", {"code": "E1"}))
        self.assertNotEqual(_fingerprint("github-brain", "Build failed", {}),
                            _fingerprint("azure-brain", "Build failed", {}))

    def test_severity(self):
        self.assertEqual(_severity("credential leak detected", ""), "critical")
        self.assertEqual(_severity("timeout while running", ""), "high")
        self.assertEqual(_severity("something odd", ""), "medium")


if __name__ == "__main__":
    unittest.main()
