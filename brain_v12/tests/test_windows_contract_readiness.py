"""Tests for secret-safe Windows contract readiness diagnostics."""
import json
import tempfile
import unittest
from pathlib import Path
from brain_v12.brain.windows_contract_readiness import readiness_snapshot

class WindowsContractReadinessTests(unittest.TestCase):
    def test_missing_secrets_fail_closed_without_values(self):
        result = readiness_snapshot({})
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["secrets"]["BRAIN_AUTHORITY_PRIVATE_KEY_B64"])
        rendered = json.dumps(result)
        self.assertNotIn("PRIVATE_KEY_VALUE", rendered)
        self.assertNotIn("approval-token", rendered)

    def test_presence_and_json_files_are_preflight_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = {}
            for name in ("identity", "checkpoint", "leadership_lease", "owner_approval"):
                path = Path(tmp) / (name + ".json")
                path.write_text('{"fixture":true}', encoding="utf-8")
                paths[name] = str(path)
            env = {
                "BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY": "delivery-secret-fixture",
                "BRAIN_AUTHORITY_PRIVATE_KEY_B64": "private-key-fixture",
                "BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64": "public-key-fixture",
                "BRAIN_HUMAN_APPROVAL_TOKEN": "human-token-fixture",
                "BRAIN_IDENTITY_FILE": paths["identity"],
                "BRAIN_CHECKPOINT_FILE": paths["checkpoint"],
                "BRAIN_LEADERSHIP_LEASE_FILE": paths["leadership_lease"],
                "BRAIN_OWNER_APPROVAL_FILE": paths["owner_approval"],
            }
            result = readiness_snapshot(env)
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "PREFLIGHT_INPUTS_PRESENT")
            self.assertTrue(all(result["secrets"].values()))
            self.assertTrue(all(x["readable_json_object"] for x in result["files"].values()))
            rendered = json.dumps(result)
            for secret in ("delivery-secret-fixture", "private-key-fixture", "public-key-fixture", "human-token-fixture"):
                self.assertNotIn(secret, rendered)
            self.assertIn("does-not-issue-contract", result["scope"])

    def test_invalid_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("not-json", encoding="utf-8")
            env = {key: str(path) for key in (
                "BRAIN_IDENTITY_FILE", "BRAIN_CHECKPOINT_FILE",
                "BRAIN_LEADERSHIP_LEASE_FILE", "BRAIN_OWNER_APPROVAL_FILE")}
            result = readiness_snapshot(env)
            self.assertFalse(result["ok"])
            self.assertTrue(all(not x["readable_json_object"] for x in result["files"].values()))

if __name__ == "__main__":
    unittest.main()
