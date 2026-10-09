import base64, time, unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from brain_v12.brain.owner_cryptographic_approval import *

class OwnerApprovalTests(unittest.TestCase):
 def setUp(self):
  self.k=Ed25519PrivateKey.generate(); self.pub=base64.b64encode(self.k.public_key().public_bytes_raw()).decode()
  self.a={"schema":SCHEMA,"owner_id":"owner-1","challenge_id":"c-1","scope":"windows-server-2025-real-boot","expires_at":2000.0}
  self.a["signature"]=base64.b64encode(self.k.sign(approval_payload(self.a["owner_id"],self.a["challenge_id"],self.a["scope"],self.a["expires_at"]))).decode()
 def test_valid(self): self.assertEqual(verify_owner_approval(self.a,self.pub,now=1000).scope,self.a["scope"])
 def test_expired(self):
  with self.assertRaisesRegex(ValueError,"OWNER_APPROVAL_EXPIRED"): verify_owner_approval(self.a,self.pub,now=2000)
 def test_replay(self):
  with self.assertRaisesRegex(ValueError,"OWNER_APPROVAL_REPLAY"): verify_owner_approval(self.a,self.pub,now=1000,used_challenges={"c-1"})
 def test_tamper(self):
  self.a["scope"]="other"
  with self.assertRaisesRegex(ValueError,"OWNER_APPROVAL_SIGNATURE_INVALID"): verify_owner_approval(self.a,self.pub,now=1000)
 def test_bad_schema(self):
  self.a["schema"]="x"
  with self.assertRaisesRegex(ValueError,"OWNER_APPROVAL_SCHEMA_INVALID"): verify_owner_approval(self.a,self.pub,now=1000)
if __name__=="__main__": unittest.main()
