import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from brain_v12.tools.blocker_to_action import classify, classify_many
from brain_v12.tools.cloud_secret_readiness import inspect_presence
from brain_v12.tools.runner_capability_preflight import inspect_capabilities
from brain_v12.tools.golden_checkpoint_verify import verify_checkpoint


class BrainFoundationToolsTests(unittest.TestCase):
    def test_blocker_maps_contract_failure_to_action(self):
        result = classify({"reason": "WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED"})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("signed", result["next_action"])
        self.assertEqual(result["source_mutation"], "NONE")

    def test_blocker_deduplicates_same_code(self):
        result = classify_many([{"blocker_code": "API_PERMISSION_DENIED"}, {"blocker_code": "API_PERMISSION_DENIED"}])
        self.assertEqual(result["blocker_count"], 1)

    def test_secret_readiness_only_reports_presence(self):
        result = inspect_presence(["SAFE_NAME", "MISSING"], {"SAFE_NAME": "do-not-emit"})
        self.assertFalse(result["ready"])
        self.assertEqual(result["missing_names"], ["MISSING"])
        self.assertNotIn("do-not-emit", json.dumps(result))

    def test_runner_preflight_does_not_claim_boot(self):
        result = inspect_capabilities(
            environ={},
            system="Linux",
            machine="x86_64",
            exists=lambda _: False,
            which=lambda _: None,
        )
        self.assertFalse(result["ready"])
        self.assertFalse(result["windows_boot_verified"])
        self.assertFalse(result["cloud_resources_changed"])

    def test_checkpoint_hash_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "state.bin"
            payload.write_bytes(b"brain-state")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"files": [{"path": "state.bin", "sha256": hashlib.sha256(b"brain-state").hexdigest()}]}))
            result = verify_checkpoint(manifest, root)
            self.assertTrue(result["verified"])
            self.assertFalse(result["restore_performed"])
            payload.write_bytes(b"changed")
            self.assertFalse(verify_checkpoint(manifest, root)["verified"])


if __name__ == "__main__":
    unittest.main()
