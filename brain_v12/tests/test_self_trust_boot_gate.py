import tempfile
import unittest
from pathlib import Path

from brain_v12.brain.self_trust_boot_gate import (
    BOOT_GATE_VERSION,
    BootGateEvidence,
    evaluate,
    evaluate_from_observations,
)


class SelfTrustBootGateTests(unittest.TestCase):
    def test_all_evidence_reaches_brain_ready(self):
        result = evaluate(BootGateEvidence(True, True, True, True, "task-1"))
        self.assertTrue(result.ok)
        self.assertEqual(result.status, "BRAIN_READY")
        self.assertEqual(result.gate, BOOT_GATE_VERSION)
        self.assertEqual(result.failed_checks, ())

    def test_missing_self_test_blocks_boot(self):
        result = evaluate(BootGateEvidence(True, True, True, False, "task-2"))
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "BRAIN_BOOT_BLOCKED")
        self.assertEqual(result.failed_checks, ("SELF_TEST_NOT_VERIFIED",))

    def test_missing_trust_root_blocks_boot(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = evaluate_from_observations(
                runtime_ready=True,
                agent_online=True,
                self_test_verified=True,
                task_id="task-3",
                trust_root=str(Path(tmp) / "missing.key"),
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.failed_checks, ("TRUST_ROOT_MISSING",))

    def test_present_trust_root_allows_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / "agent.key"
            key.write_text("test-only", encoding="utf-8")
            result = evaluate_from_observations(
                runtime_ready=True,
                agent_online=True,
                self_test_verified=True,
                task_id="task-4",
                trust_root=str(key),
            )
        self.assertTrue(result.ok)
        self.assertEqual(result.status, "BRAIN_READY")


if __name__ == "__main__":
    unittest.main()
