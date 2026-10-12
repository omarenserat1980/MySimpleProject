import base64, os, tempfile, unittest
from dataclasses import replace
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
                 "scope":"windows-server-2025-real-boot","expires_at":2000.0,
                 "source_commit":"a"*40,"task_id":"windows-real-boot","attempt_id":"attempt-1"}
  self.approval["signature"]=base64.b64encode(self.k.sign(
   approval_payload(self.approval["owner_id"],self.approval["challenge_id"],
                    self.approval["scope"],self.approval["expires_at"],self.approval["source_commit"],
                    self.approval["task_id"],self.approval["attempt_id"]))).decode()
 def identity(self):
  return {"schema":IDENTITY_SCHEMA,"brain_id":"brain-primary","generation":2,
          "source_commit":"a"*40,"checkpoint_id":"BRAIN-GOLDEN-01"}
 def checkpoint(self):
  return {"checkpoint_id":"BRAIN-GOLDEN-01","source_commit":"a"*40,"status":"STABLE_BASELINE"}
 def test_contract_cannot_outlive_owner_approval(self):
  old=os.environ.get("BRAIN_HUMAN_APPROVAL_TOKEN"); oldkey=os.environ.get("BRAIN_AUTHORITY_PRIVATE_KEY_B64")
  os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]="approval-secret"
  os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=base64.b64encode(self.k.private_bytes_raw()).decode()
  try:
   approval=dict(self.approval); approval["expires_at"]=150.0
   approval["signature"]=base64.b64encode(self.k.sign(approval_payload(
    approval["owner_id"],approval["challenge_id"],approval["scope"],approval["expires_at"],
    approval["source_commit"],approval["task_id"],approval["attempt_id"]))).decode()
   with tempfile.TemporaryDirectory() as d:
    store=BrainLeadershipStore(Path(d)/"leadership.db")
    lease=store.acquire(self.identity(),self.checkpoint(),"windows-real-boot-qemu",now=100)
    try:
     with self.assertRaisesRegex(RuntimeError,"OWNER_APPROVAL_EXPIRY_TOO_SOON"):
      issue_windows_contract(identity=self.identity(),checkpoint=self.checkpoint(),lease=lease,
       source_commit="a"*40,task_id="windows-real-boot",attempt_id="attempt-1",
       capability_verified=True,human_approval_token="approval-secret",
       owner_approval=approval,owner_public_key_b64=self.pub,now=100)
    finally: store.close()
  finally:
   if old is None: os.environ.pop("BRAIN_HUMAN_APPROVAL_TOKEN",None)
   else: os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]=old
   if oldkey is None: os.environ.pop("BRAIN_AUTHORITY_PRIVATE_KEY_B64",None)
   else: os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=oldkey
 def test_owner_approval_is_required(self):
  with tempfile.TemporaryDirectory() as d:
   store=BrainLeadershipStore(Path(d)/"leadership.db")
   lease=store.acquire(self.identity(),self.checkpoint(),"windows-real-boot-qemu",now=100)
   try:
    with self.assertRaisesRegex(RuntimeError,"OWNER_APPROVAL_REQUIRED"):
     issue_windows_contract(identity=self.identity(),checkpoint=self.checkpoint(),lease=lease,
      source_commit="a"*40,task_id="windows-real-boot",attempt_id="attempt-1",
      capability_verified=True,human_approval_token="approval-secret",now=100)
   finally: store.close()
 def test_issuer_accepts_valid_owner_approval(self):
  old=os.environ.get("BRAIN_HUMAN_APPROVAL_TOKEN"); oldkey=os.environ.get("BRAIN_AUTHORITY_PRIVATE_KEY_B64")
  os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]="approval-secret"
  os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=base64.b64encode(self.k.private_bytes_raw()).decode()
  try:
   with tempfile.TemporaryDirectory() as d:
    store=BrainLeadershipStore(Path(d)/"leadership.db")
    lease=store.acquire(self.identity(),self.checkpoint(),"windows-real-boot-qemu",now=100)
    try:
     contract=issue_windows_contract(identity=self.identity(),checkpoint=self.checkpoint(),lease=lease,
      source_commit="a"*40,task_id="windows-real-boot",attempt_id="attempt-1",
      capability_verified=True,human_approval_token="approval-secret",
      owner_approval=self.approval,owner_public_key_b64=self.pub,now=100)
    finally: store.close()
  finally:
   if old is None: os.environ.pop("BRAIN_HUMAN_APPROVAL_TOKEN",None)
   else: os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]=old
   if oldkey is None: os.environ.pop("BRAIN_AUTHORITY_PRIVATE_KEY_B64",None)
   else: os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=oldkey
  self.assertEqual(contract["status"],"VERIFIED")
  self.assertEqual(contract["authority_decision"],"AUTHORIZED")
  self.assertEqual(contract["owner_id"],"owner-1")
  self.assertEqual(contract["owner_scope"],"windows-server-2025-real-boot")

 def test_contract_cannot_outlive_leadership_lease(self):
  old=os.environ.get("BRAIN_HUMAN_APPROVAL_TOKEN"); oldkey=os.environ.get("BRAIN_AUTHORITY_PRIVATE_KEY_B64")
  os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]="approval-secret"
  os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=base64.b64encode(self.k.private_bytes_raw()).decode()
  try:
   with tempfile.TemporaryDirectory() as d:
    store=BrainLeadershipStore(Path(d)/"leadership.db")
    lease=store.acquire(self.identity(),self.checkpoint(),"windows-real-boot-qemu",now=100)
    lease=replace(lease,expires_at=250.0)
    try:
     contract=issue_windows_contract(identity=self.identity(),checkpoint=self.checkpoint(),lease=lease,
      source_commit="a"*40,task_id="windows-real-boot",attempt_id="attempt-1",
      capability_verified=True,human_approval_token="approval-secret",
      owner_approval=self.approval,owner_public_key_b64=self.pub,now=100)
     self.assertEqual(contract["expires_at"],250.0)
    finally: store.close()
  finally:
   if old is None: os.environ.pop("BRAIN_HUMAN_APPROVAL_TOKEN",None)
   else: os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]=old
   if oldkey is None: os.environ.pop("BRAIN_AUTHORITY_PRIVATE_KEY_B64",None)
   else: os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=oldkey

 def test_contract_rejects_nearly_expired_leadership_lease(self):
  old=os.environ.get("BRAIN_HUMAN_APPROVAL_TOKEN"); oldkey=os.environ.get("BRAIN_AUTHORITY_PRIVATE_KEY_B64")
  os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]="approval-secret"
  os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=base64.b64encode(self.k.private_bytes_raw()).decode()
  try:
   with tempfile.TemporaryDirectory() as d:
    store=BrainLeadershipStore(Path(d)/"leadership.db")
    lease=store.acquire(self.identity(),self.checkpoint(),"windows-real-boot-qemu",now=100)
    lease=replace(lease,expires_at=150.0)
    try:
     with self.assertRaisesRegex(RuntimeError,"LEADERSHIP_LEASE_EXPIRY_TOO_SOON"):
      issue_windows_contract(identity=self.identity(),checkpoint=self.checkpoint(),lease=lease,
       source_commit="a"*40,task_id="windows-real-boot",attempt_id="attempt-1",
       capability_verified=True,human_approval_token="approval-secret",
       owner_approval=self.approval,owner_public_key_b64=self.pub,now=100)
    finally: store.close()
  finally:
   if old is None: os.environ.pop("BRAIN_HUMAN_APPROVAL_TOKEN",None)
   else: os.environ["BRAIN_HUMAN_APPROVAL_TOKEN"]=old
   if oldkey is None: os.environ.pop("BRAIN_AUTHORITY_PRIVATE_KEY_B64",None)
   else: os.environ["BRAIN_AUTHORITY_PRIVATE_KEY_B64"]=oldkey

if __name__=="__main__": unittest.main()
