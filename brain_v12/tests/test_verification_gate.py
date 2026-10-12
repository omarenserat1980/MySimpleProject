import unittest

from brain_v12.brain.verification_gate import VerificationGate, VerificationError


class VerificationGateTests(unittest.TestCase):
    def test_completed_action_is_not_objective_completion(self):
        result = VerificationGate.evaluate({"ok": True, "status": "COMPLETED"})
        self.assertTrue(result["action_verified"])
        self.assertFalse(result["objective_verified"])
        self.assertEqual(result["status"], "ACTION_VERIFIED")

    def test_objective_completion_requires_evidence(self):
        result = VerificationGate.evaluate({
            "ok": True, "status": "COMPLETED", "objective_verified": True
        })
        self.assertFalse(result["objective_verified"])
        self.assertEqual(result["reason"], "OBJECTIVE_VERIFICATION_REQUIRES_EVIDENCE")

    def test_objective_completion_with_evidence_is_verified(self):
        result = VerificationGate.evaluate({
            "ok": True, "status": "COMPLETED",
            "objective_verified": True,
            "objective_verification": {"passed": True, "criterion": "task_result.json exists and is valid"},
            "evidence": {"artifact": "task_result.json", "sha256": "abc"},
        })
        self.assertTrue(result["objective_verified"])
        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["evidence_ref"].startswith("evidence://sha256/"))

    def test_failed_action_cannot_be_objective_verified(self):
        result = VerificationGate.evaluate({
            "ok": False, "status": "FAILED",
            "objective_verified": True,
            "evidence": {"failure": "timeout"},
        })
        self.assertFalse(result["objective_verified"])

    def test_require_raises_for_unverified_result(self):
        with self.assertRaises(VerificationError):
            VerificationGate.require_objective_verification({
                "ok": True, "status": "COMPLETED"
            })


    def test_objective_boolean_alone_is_rejected(self):
        result = VerificationGate.evaluate({"ok": True, "status": "COMPLETED", "objective_verified": True, "evidence": {"artifact": "task_result.json"}})
        self.assertFalse(result["objective_verified"])
        self.assertEqual(result["reason"], "OBJECTIVE_VERIFICATION_CONTRACT_REQUIRED")

if __name__ == "__main__":
    unittest.main()
