import json
import tempfile
import unittest
from pathlib import Path

from brain_phone_base.local_executor import LocalExecutor


class LocalExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "brain_phone_base").mkdir()
        (self.root / "evidence").mkdir()
        self.executor = LocalExecutor(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_allowlist_rejects_arbitrary_shell(self):
        self.assertEqual(
            set(self.executor.actions()),
            {"status", "test-measurement", "test-local-executor", "measure", "verify-evidence"},
        )
        with self.assertRaisesRegex(ValueError, "ACTION_NOT_ALLOWED"):
            self.executor.enqueue("rm -rf /")

    def test_queue_and_hash_chained_audit(self):
        task = self.executor.enqueue("verify-evidence")
        self.assertEqual(task["status"], "queued")
        lines = (self.root / ".brain_local_executor" / "audit.jsonl").read_text().splitlines()
        record = json.loads(lines[0])
        self.assertEqual(record["event"], "task_queued")
        self.assertEqual(record["previous_hash"], "0" * 64)
        self.assertEqual(len(record["event_hash"]), 64)

    def test_no_evidence_fails_closed(self):
        result = self.executor.verify_evidence()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["independent_identity_verification"], "NOT_PERFORMED")
        self.assertEqual(result["mining"], "DISABLED")

    def test_valid_safe_evidence_only_passes_local_contract(self):
        data = {
            "schema": "brain-phone-base.real-measurement.v1",
            "measured_at_utc": "2026-10-15T15:00:00Z",
            "evidence": {
                "device_identity_verified": False,
                "independent_verification": "not_performed",
                "integrity_signature": None,
            },
            "node_gate": {
                "state": "untrusted_inactive",
                "trusted": False,
                "active": False,
                "activation_allowed": False,
                "manual_approval": "not_granted",
            },
            "network_actions": {
                "measurement_uploaded": False,
                "node_registered": False,
                "mining_started": False,
                "mining_pool_contacted": False,
            },
        }
        (self.root / "evidence" / "phone-real-measurement.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        result = self.executor.verify_evidence()
        self.assertEqual(result["status"], "PASS_LOCAL_CONTRACT_ONLY")
        self.assertEqual(result["independent_identity_verification"], "NOT_PERFORMED")
        self.assertEqual(result["node_activation"], "PROHIBITED_BY_DEFAULT")


if __name__ == "__main__":
    unittest.main()
