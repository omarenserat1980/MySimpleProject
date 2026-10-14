import unittest
from brain_v12.design_factory.evidence import classify_evidence
class EvidenceTests(unittest.TestCase):
 def test_simulation_cannot_prove_hardware(self):
  r=classify_evidence("HARDWARE_VERIFIED",simulation_only=True,evidence_present=True,independent_review=True)
  self.assertFalse(r["accepted"]); self.assertEqual(r["status"],"BLOCKED")
 def test_verified_without_evidence_is_blocked(self):
  r=classify_evidence("VERIFIED",evidence_present=False,independent_review=True)
  self.assertFalse(r["accepted"]); self.assertEqual(r["status"],"BLOCKED")
 def test_verified_requires_independent_review(self):
  r=classify_evidence("VERIFIED",evidence_present=True,independent_review=False)
  self.assertFalse(r["accepted"]); self.assertEqual(r["status"],"BLOCKED")
 def test_simulated_requires_explicit_simulation_flag(self):
  self.assertFalse(classify_evidence("SIMULATED",simulation_only=False)["accepted"])
 def test_unknown_status_is_rejected(self):
  with self.assertRaises(ValueError): classify_evidence("MAGICALLY_DONE")
 def test_planned_can_be_recorded_without_evidence(self):
  self.assertTrue(classify_evidence("PLANNED")["accepted"])
if __name__=="__main__": unittest.main()
