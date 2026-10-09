import base64,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from brain_v12.brain.owner_cryptographic_approval import SCHEMA,approval_payload
from brain_v12.brain.owner_bound_arkan_promotion_gate import OwnerBoundArkanPromotionGate

class OwnerBoundGateTests(unittest.TestCase):
 def setUp(self):
  self.k=Ed25519PrivateKey.generate(); self.pub=base64.b64encode(self.k.public_key().public_bytes_raw()).decode()
  self.g=OwnerBoundArkanPromotionGate(self.pub)
  self.t={"ok":True,"status":"GOLDEN_CLOSED_LOOP_VERIFIED","evidence_ids":["e1"],"authority_verified":True,"leadership_verified":True,"resource_verified":True}
  self.p={"heartbeat":"FRESH","task_evidence":True,"verification":"VERIFIED"}
 def approval(self,scope="windows-server-2025-real-boot"):
  a={"schema":SCHEMA,"owner_id":"owner-1","challenge_id":"unique-1","scope":scope,"expires_at":2000.0}
  a["signature"]=base64.b64encode(self.k.sign(approval_payload(a["owner_id"],a["challenge_id"],a["scope"],a["expires_at"]))).decode(); return a
 def test_owner_required(self): self.assertFalse(self.g.evaluate(self.t,self.p,None,now=1000)["allowed"])
 def test_valid_owner_allows(self): self.assertTrue(self.g.evaluate(self.t,self.p,self.approval(),now=1000)["allowed"])
 def test_scope_mismatch_blocks(self): self.assertFalse(self.g.evaluate(self.t,self.p,self.approval("other"),now=1000)["allowed"])
 def test_replay_blocks(self):
  a=self.approval(); self.assertTrue(self.g.evaluate(self.t,self.p,a,now=1000)["allowed"])
  self.assertFalse(self.g.evaluate(self.t,self.p,a,now=1000)["allowed"])
if __name__=="__main__": unittest.main()
