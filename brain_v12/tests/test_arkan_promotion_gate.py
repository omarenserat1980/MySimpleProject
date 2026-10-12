import unittest
from brain_v12.brain.arkan_promotion_gate import ArkanPromotionGate

class PromotionGateTests(unittest.TestCase):
 def setUp(self): self.g=ArkanPromotionGate()
 def twin(self,**kw):
  x={"ok":True,"status":"GOLDEN_CLOSED_LOOP_VERIFIED","evidence_ids":["e1"],
     "authority_verified":True,"leadership_verified":True,"resource_verified":True}
  x.update(kw); return x
 def test_fail_closed_without_real_probe(self):
  d=self.g.evaluate(self.twin()); self.assertFalse(d.allowed); self.assertIn("REAL_PROBE_REQUIRED",d.reasons)
 def test_blocks_fake_real_success(self):
  d=self.g.evaluate(self.twin(),{"heartbeat":"FRESH","task_evidence":False,"verification":"VERIFIED"})
  self.assertFalse(d.allowed); self.assertIn("REAL_TASK_EVIDENCE_REQUIRED",d.reasons)
 def test_all_real_gates_required(self):
  d=self.g.evaluate(self.twin(),{"heartbeat":"FRESH","task_evidence":True,"verification":"VERIFIED"})
  self.assertTrue(d.allowed); self.assertEqual(d.status,"PROMOTION_ALLOWED")
 def test_twin_failure_blocks(self):
  d=self.g.evaluate(self.twin(ok=False)); self.assertFalse(d.allowed)
if __name__=="__main__": unittest.main()
