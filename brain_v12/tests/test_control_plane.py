import unittest
from brain_v12.brain.control_plane import BrainControlPlane


class BrainControlPlaneTests(unittest.TestCase):
    def test_success_requires_verification_and_evidence(self):
        cp = BrainControlPlane()
        task = cp.create("run verified task")
        result = cp.execute(task["id"], lambda _: {"returncode": 0}, lambda _: {"verified": True})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "VERIFICATION_EVIDENCE_REQUIRED")
        self.assertNotEqual(result["status"], "VERIFIED_COMPLETED")

    def test_verified_execution_completes(self):
        cp = BrainControlPlane()
        task = cp.create("run verified task")
        result = cp.execute(task["id"], lambda _: {"returncode": 0}, lambda _: {"verified": True, "evidence_ref": "test://run/1"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "VERIFIED_COMPLETED")
        self.assertEqual(result["task"]["attempts"], 1)

    def test_failed_verification_is_bounded(self):
        cp = BrainControlPlane()
        task = cp.create("repair task", max_attempts=2)
        first = cp.execute(task["id"], lambda _: {"returncode": 1}, lambda _: {"verified": False})
        self.assertEqual(first["status"], "RETRYING")
        second = cp.execute(task["id"], lambda _: {"returncode": 1}, lambda _: {"verified": False})
        self.assertEqual(second["status"], "FAILED")
        self.assertEqual(second["error"], "VERIFICATION_FAILED")
        third = cp.execute(task["id"], lambda _: {"returncode": 0}, lambda _: {"verified": True, "evidence_ref": "test://late"})
        self.assertFalse(third["ok"])
        self.assertEqual(third["error"], "RETRY_LIMIT_REACHED")

    def test_executor_exception_never_claims_success(self):
        cp = BrainControlPlane()
        task = cp.create("unsafe task")
        result = cp.execute(task["id"], lambda _: (_ for _ in ()).throw(RuntimeError("boom")), lambda _: {"verified": True, "evidence_ref": "test://never"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "EXECUTOR_ERROR:RuntimeError")

    def test_quran_external_evidence_is_attached_only_when_verified(self):
        cp = BrainControlPlane()
        task = cp.create("quran layer audit")
        result = cp.attach_verified_evidence(task["id"], {"verified": True, "evidence_ref": "repo://quran_layer_audit"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["task"]["evidence"][-1]["stage"], "external_verification")
        rejected = cp.attach_verified_evidence(task["id"], {"verified": False, "evidence_ref": "repo://bad"})
        self.assertFalse(rejected["ok"])

    def test_external_evidence_requires_reference(self):
        cp = BrainControlPlane()
        task = cp.create("quran layer audit")
        result = cp.attach_verified_evidence(task["id"], {"verified": True})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "EVIDENCE_REFERENCE_REQUIRED")


if __name__ == "__main__":
    unittest.main()
