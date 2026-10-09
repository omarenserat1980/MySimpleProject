import unittest
from brain_v12.brain.real_arkan_probe import RealArkanProbeValidator

class RealArkanProbeTests(unittest.TestCase):
 def setUp(self): self.v=RealArkanProbeValidator()
 def base(self):
  return {"device_id":"arkan","heartbeat_at":"2026-10-09T08:00:00+03:00","task_id":"probe-1",
          "task_evidence":True,"verification":"VERIFIED","heartbeat":"FRESH","reality":"REAL"}
 def test_valid_real_evidence(self):
  p=self.v.validate(self.base()); self.assertEqual(p.verification,"VERIFIED"); self.assertEqual(len(p.evidence_hash),64)
 def test_twin_is_rejected(self):
  x=self.base(); x["reality"]="SIMULATED"
  with self.assertRaisesRegex(ValueError,"REALITY_MUST_BE_REAL"): self.v.validate(x)
 def test_stale_heartbeat_rejected(self):
  x=self.base(); x["heartbeat"]="STALE"
  with self.assertRaisesRegex(ValueError,"FRESH_REAL_HEARTBEAT_REQUIRED"): self.v.validate(x)
 def test_missing_task_evidence_rejected(self):
  x=self.base(); x["task_evidence"]=False
  with self.assertRaisesRegex(ValueError,"REAL_TASK_EVIDENCE_REQUIRED"): self.v.validate(x)
 def test_unverified_rejected(self):
  x=self.base(); x["verification"]="FAILED"
  with self.assertRaisesRegex(ValueError,"INDEPENDENT_VERIFICATION_REQUIRED"): self.v.validate(x)
if __name__=="__main__": unittest.main()
