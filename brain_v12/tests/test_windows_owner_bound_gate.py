import base64, json, os, tempfile, time, unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from brain_v12.brain.authority_signature import ALGORITHM, sign_contract
from brain_v12.brain.windows_real_boot_closed_loop_gate import load_and_verify

class WindowsOwnerBoundGateTests(unittest.TestCase):
 def setUp(self):
  self.k=Ed25519PrivateKey.generate()
  self.pub=base64.b64encode(self.k.public_key().public_bytes_raw()).decode()
  self.old=os.environ.get("BRAIN_AUTHORITY_PUBLIC_KEY_B64"); os.environ["BRAIN_AUTHORITY_PUBLIC_KEY_B64"]=self.pub
  self.addCleanup(self.cleanup)
 def cleanup(self):
  if self.old is None: os.environ.pop("BRAIN_AUTHORITY_PUBLIC_KEY_B64",None)
  else: os.environ["BRAIN_AUTHORITY_PUBLIC_KEY_B64"]=self.old
 def contract(self):
  c={"schema":"brain.windows-execution-contract.v1","status":"VERIFIED","capability":"windows-server-2025-real-boot",
     "executor":"windows-real-boot-qemu","authority_policy_version":"authority-policy-v1","authority_decision":"AUTHORIZED",
     "brain_id":"brain-test","generation":7,"fencing_token":19,"lease_id":"lease-19","holder_id":"cloud-qemu-01",
     "task_id":"windows-real-boot","attempt_id":"attempt-abc","source_commit":"a"*40,
     "owner_id":"owner-1","owner_challenge_id":"challenge-1","owner_scope":"windows-server-2025-real-boot",
     "expires_at":time.time()+300,"authority_signature_algorithm":ALGORITHM}
  c["authority_signature"]=sign_contract(c,base64.b64encode(self.k.private_bytes_raw()).decode()); return c
 def write(self,c):
  f=tempfile.NamedTemporaryFile("w",encoding="utf-8",delete=False); json.dump(c,f); f.close(); self.addCleanup(lambda: os.unlink(f.name)); return f.name
 def test_accepts_owner_bound_contract(self):
  old=os.environ.get("GITHUB_SHA"); os.environ["GITHUB_SHA"]="a"*40
  try: self.assertTrue(load_and_verify(self.write(self.contract()))["verified"])
  finally:
   if old is None: os.environ.pop("GITHUB_SHA",None)
   else: os.environ["GITHUB_SHA"]=old
 def test_missing_owner_rejected(self):
  c=self.contract(); c.pop("owner_id")
  with self.assertRaisesRegex(RuntimeError,"OWNER_ID_REQUIRED"): load_and_verify(self.write(c))
 def test_owner_tamper_breaks_signature(self):
  c=self.contract(); c["owner_id"]="tampered-owner"
  with self.assertRaisesRegex(RuntimeError,"AUTHORITY_SIGNATURE_INVALID"): load_and_verify(self.write(c))
if __name__=="__main__": unittest.main()
