import base64, tempfile, unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from brain_v12.brain.brain_identity import IDENTITY_SCHEMA
from brain_v12.brain.brain_leadership import BrainLeadershipStore
from brain_v12.brain.owner_cryptographic_approval import SCHEMA, approval_payload
from brain_v12.brain.windows_execution_contract_issuer import issue_windows_contract

class WindowsExecutionContractIssuerTests(unittest.TestCase):
 def setUp(self):
  self.k=Ed25519PrivateKey.generate()
  self.pub=base64.b64encode(self.k.public_key().public_bytes_raw()).decode()
  self.approval={"schema":SCHEMA,"owner_id":"owner-1","challenge_id":"contract-test-1",
                 "scope":"windows-server-2025-real-boot","expires_at":2000.0}
  self.approval["signature"]=base64.b64encode(self.k.sign(
      approval_payload(self.approval["owner_id"],self.approval["challenge_id"],
                       self.approval["scope"],self.approval["expires_at"]))).decode()
 def identity(self):
  return {"schema":IDENTITY_SCHEMA,"brain_id":"brain-primary","generation":2,
          "source_commit":"a"*40,"checkpoint_id":"BRAIN-GOLDEN-01"}
 def checkpoint(self):
  return {"checkpoint_id":"BRAIN-GOLDEN-01","source_commit":"a"*40,"status":"STABLE_BASELINE"}
 def test_owner_approval_is_required(self):
  with tempfile.TemporaryDirectory() as d:
   store=BrainLeadershipStore(Path(d)/"leadership.db"); lease=store.acquire(self.identity(),self.checkpoint(),"windows-real-boot-qemu",now=100)
   try:
    with self.assertRaisesRegex(RuntimeError,"OWNER_APPROVAL_REQUIRED"):
     issue_windows_contract(identity=self.identity(),checkpoint=self.checkpoint(),lease=lease,
      source_commit="a"*40,task_id="windows-real-boot",attempt_id="attempt-1",
      capability_verified=True,human_approval_token="approval-secret",now=100)
   finally: store.close()
 def test_issuer_accepts_valid_owner_approval(self):
  with tempfile.TemporaryDirectory() as d:
   store=BrainLeadershipStore(Path(d)/"leadership.db"); lease=store.acquire(self.identity(),self.checkpoint(),"windows-real-boot-qemu",now=100)
   try:
    contract=issue_windows_contract(identity=self.identity(),checkpoint=self.checkpoint(),lease=lease,
     source_commit="a"*40,task_id="windows-real-boot",attempt_id="attempt-1",
     capability_verified=True,human_approval_token="approval-secret",
     owner_approval=self.approval,owner_public_key_b64=self.pub,now=100)
   finally: store.close()
  self.assertEqual(contract["status"],"VERIFIED")
  self.assertEqual(contract["authority_decision"],"AUTHORIZED")
  self.assertEqual(contract["fencing_token"],1)
  self.assertEqual(contract["owner_id"],"owner-1")
  self.assertEqual(contract["owner_scope"],"windows-server-2025-real-boot")
 if __name__=="__main__": unittest.main()
