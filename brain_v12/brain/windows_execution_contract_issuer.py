"""Brain-issued Windows real-boot execution contract."""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from typing import Any
from .brain_authority import BrainAuthorityPolicy, require_authorized
from .authority_signature import sign_contract, ALGORITHM
from .brain_identity import require_checkpoint_identity
from .brain_leadership import BrainLeadershipStore, LeadershipLease
from .owner_cryptographic_approval import verify_owner_approval

SCHEMA="brain.windows-execution-contract.v1"
CAPABILITY="windows-server-2025-real-boot"
EXECUTOR="windows-real-boot-qemu"
POLICY="authority-policy-v1"

def _load(path: str, error: str) -> dict[str, Any]:
    p=Path(path)
    if not p.is_file(): raise RuntimeError(error)
    try: d=json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc: raise RuntimeError(error) from exc
    if not isinstance(d,dict): raise RuntimeError(error)
    return d

def issue_windows_contract(*, identity:dict[str,Any], checkpoint:dict[str,Any],
    lease:LeadershipLease, source_commit:str, task_id:str, attempt_id:str,
    capability_verified:bool, human_approval_token:str|None=None,
    owner_approval:dict[str,Any]|None=None, owner_public_key_b64:str|None=None,
    now:float|None=None, expires_seconds:int=900)->dict[str,Any]:
    verified=require_checkpoint_identity(identity,checkpoint)
    source_commit=str(source_commit).strip().lower()
    if len(source_commit)!=40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_SOURCE_COMMIT_INVALID")
    if source_commit!=verified["source_commit"]: raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_SOURCE_COMMIT_MISMATCH")
    if not capability_verified: raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_CAPABILITY_NOT_VERIFIED")
    if str(task_id).strip()=="" or str(attempt_id).strip()=="": raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_TASK_ATTEMPT_REQUIRED")
    if lease.holder_id=="" or lease.fencing_token<1: raise RuntimeError("BRAIN_LEADERSHIP_LEASE_INVALID")
    if owner_approval is None: raise RuntimeError("OWNER_APPROVAL_REQUIRED")
    if not owner_public_key_b64: raise RuntimeError("OWNER_APPROVAL_PUBLIC_KEY_REQUIRED")
    owner=verify_owner_approval(owner_approval,owner_public_key_b64,now=now)
    if owner.scope != CAPABILITY: raise RuntimeError("OWNER_APPROVAL_SCOPE_MISMATCH")
    decision=BrainAuthorityPolicy().decide(subject=EXECUTOR,action="windows-real-boot",risk="HIGH",capability=True,human_approval_token=human_approval_token)
    require_authorized(decision)
    now=time.time() if now is None else float(now)
    if expires_seconds<60: raise RuntimeError("WINDOWS_EXECUTION_CONTRACT_EXPIRY_TOO_SHORT")
    c={"schema":SCHEMA,"status":"VERIFIED","capability":CAPABILITY,"executor":EXECUTOR,
       "authority_policy_version":POLICY,"authority_decision":"AUTHORIZED",
       "brain_id":verified["brain_id"],"generation":verified["generation"],
       "fencing_token":lease.fencing_token,"lease_id":lease.lease_id,"holder_id":lease.holder_id,
       "task_id":str(task_id).strip(),"attempt_id":str(attempt_id).strip(),
       "source_commit":source_commit,"issued_at":now,"expires_at":now+int(expires_seconds),
       "owner_id":owner.owner_id,"owner_challenge_id":owner.challenge_id,"owner_scope":owner.scope}
    c["authority_signature_algorithm"]=ALGORITHM
    c["authority_signature"]=sign_contract(c)
    return c

def issue_from_files(*,identity_file:str,checkpoint_file:str,lease_file:str,output:str,
    source_commit:str,task_id:str,attempt_id:str,capability_verified:bool,
    human_approval_token:str|None=None, owner_approval_file:str|None=None,
    owner_public_key_b64:str|None=None)->dict[str,Any]:
    identity=_load(identity_file,"BRAIN_IDENTITY_FILE_REQUIRED")
    checkpoint=_load(checkpoint_file,"BRAIN_CHECKPOINT_FILE_REQUIRED")
    raw=_load(lease_file,"BRAIN_LEADERSHIP_LEASE_FILE_REQUIRED")
    try:
        lease=LeadershipLease(str(raw["brain_id"]),int(raw["generation"]),str(raw["lease_id"]),
            int(raw["fencing_token"]),str(raw["holder_id"]),float(raw["acquired_at"]),float(raw["expires_at"]))
    except (KeyError,TypeError,ValueError) as exc: raise RuntimeError("BRAIN_LEADERSHIP_LEASE_INVALID") from exc
    owner_approval=_load(owner_approval_file,"OWNER_APPROVAL_FILE_REQUIRED") if owner_approval_file else None
    store=BrainLeadershipStore()
    try:
        store.assert_current(lease)
        c=issue_windows_contract(identity=identity,checkpoint=checkpoint,lease=lease,source_commit=source_commit,
            task_id=task_id,attempt_id=attempt_id,
            capability_verified=capability_verified,human_approval_token=human_approval_token,
            owner_approval=owner_approval,owner_public_key_b64=owner_public_key_b64)
    finally: store.close()
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+".tmp"); tmp.write_text(json.dumps(c,indent=2,sort_keys=True),encoding="utf-8"); os.replace(tmp,out)
    return {"verified":True,"contract_path":str(out),"schema":c["schema"],"brain_id":c["brain_id"],
            "generation":c["generation"],"fencing_token":c["fencing_token"],"task_id":c["task_id"],
            "attempt_id":c["attempt_id"],"expires_at":c["expires_at"]}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--identity-file",required=True); ap.add_argument("--checkpoint-file",required=True)
    ap.add_argument("--lease-file",required=True); ap.add_argument("--output",required=True)
    ap.add_argument("--source-commit",required=True); ap.add_argument("--task-id",default="windows-real-boot")
    ap.add_argument("--attempt-id",required=True); ap.add_argument("--capability-verified",action="store_true")
    ap.add_argument("--owner-approval-file",required=True)
    a=ap.parse_args()
    print(json.dumps(issue_from_files(identity_file=a.identity_file,checkpoint_file=a.checkpoint_file,
        lease_file=a.lease_file,output=a.output,source_commit=a.source_commit,task_id=a.task_id,
        attempt_id=a.attempt_id,capability_verified=a.capability_verified,
        human_approval_token=os.environ.get("BRAIN_HUMAN_APPROVAL_TOKEN"),
        owner_approval_file=a.owner_approval_file,
        owner_public_key_b64=os.environ.get("BRAIN_OWNER_APPROVAL_PUBLIC_KEY_B64")),sort_keys=True))
