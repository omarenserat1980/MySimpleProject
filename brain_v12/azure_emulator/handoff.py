from __future__ import annotations
import hashlib,json,sqlite3,time,uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .service import AzureEmulator

@dataclass(frozen=True)
class HandoffCertificate:
    schema:str
    certificate_id:str
    issued_at:float
    expires_at:float
    evidence_sha256:str
    plan_sha256:str
    provider:str
    vm_id:str
    free_only:bool
    fencing_token:int

class HandoffLedger:
    """Durable, transactional one-shot ledger for the emulator->real-cloud boundary."""
    def __init__(self,path=" .brain/state/azure-handoff.db"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS handoffs(
          certificate_id TEXT PRIMARY KEY, evidence_sha256 TEXT NOT NULL, plan_sha256 TEXT NOT NULL,
          vm_id TEXT NOT NULL, provider TEXT NOT NULL, issued_at REAL NOT NULL, expires_at REAL NOT NULL,
          fencing_token INTEGER NOT NULL, status TEXT NOT NULL)""")
        self.db.commit()
    def issue(self,evidence:dict[str,Any],plan:dict[str,Any],ttl_seconds:int=300)->dict[str,Any]:
        cert=issue_handoff(evidence,plan,ttl_seconds=ttl_seconds)
        self.db.execute("BEGIN IMMEDIATE")
        row=self.db.execute("SELECT MAX(fencing_token) n FROM handoffs").fetchone()
        token=int(row["n"] or 0)+1
        cert["fencing_token"]=token
        self.db.execute("INSERT INTO handoffs VALUES(?,?,?,?,?,?,?,?,?)",
            (cert["certificate_id"],cert["evidence_sha256"],cert["plan_sha256"],cert["vm_id"],cert["provider"],
             cert["issued_at"],cert["expires_at"],token,"ISSUED"))
        self.db.commit()
        return cert
    def consume(self,certificate_id:str,*,now:float|None=None)->dict[str,Any]:
        now=time.time() if now is None else float(now)
        self.db.execute("BEGIN IMMEDIATE")
        row=self.db.execute("SELECT * FROM handoffs WHERE certificate_id=?",(certificate_id,)).fetchone()
        if not row: self.db.rollback(); raise RuntimeError("HANDOFF_NOT_FOUND")
        if row["status"]!="ISSUED": self.db.rollback(); raise RuntimeError("HANDOFF_ALREADY_CONSUMED")
        if float(row["expires_at"])<=now:
            self.db.execute("UPDATE handoffs SET status='EXPIRED' WHERE certificate_id=?",(certificate_id,)); self.db.commit()
            raise RuntimeError("HANDOFF_EXPIRED")
        self.db.execute("UPDATE handoffs SET status='CONSUMED' WHERE certificate_id=? AND status='ISSUED'",(certificate_id,))
        self.db.commit()
        return dict(row)
    def close(self): self.db.close()

def issue_handoff(evidence:dict[str,Any],plan:dict[str,Any],*,ttl_seconds:int=300)->dict[str,Any]:
    if not evidence.get("ok"): raise RuntimeError("HANDOFF_REQUIRES_VERIFIED_EMULATOR")
    if evidence.get("provider")!="brain-emulated-azure": raise RuntimeError("HANDOFF_PROVIDER_INVALID")
    vm=evidence.get("vm") or {}; props=vm.get("properties") or {}
    if vm.get("state")!="RUNNING" or props.get("os")!="Windows Server 2025" or props.get("architecture")!="x86_64":
        raise RuntimeError("HANDOFF_VM_NOT_VERIFIED")
    if plan.get("free_only") is not True: raise RuntimeError("HANDOFF_FREE_ONLY_REQUIRED")
    usage=evidence.get("usage") or {}; quota=evidence.get("quota") or {}
    if any(int(usage.get(k,0))>int(quota.get(k,0)) for k in ("vcpus","memory_mb","storage_gb")):
        raise RuntimeError("HANDOFF_CAPACITY_INVALID")
    ehash=hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    phash=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    now=time.time()
    return {"schema":"BRAIN-REAL-AZURE-HANDOFF-3","certificate_id":str(uuid.uuid4()),
            "issued_at":now,"expires_at":now+max(1,min(int(ttl_seconds),3600)),
            "evidence_sha256":ehash,"plan_sha256":phash,"provider":"brain-emulated-azure",
            "vm_id":vm.get("id"),"free_only":True,"single_use":True}

def certify_default_handoff()->dict[str,Any]:
    cloud=AzureEmulator(free_only=True)
    cloud.create_resource_group("brain-rg"); cloud.create_network("brain-vnet")
    cloud.create_subnet("brain-subnet","brain-vnet"); cloud.create_public_ip("brain-ip")
    cloud.create_nic("brain-nic","brain-subnet","brain-ip"); cloud.create_disk("brain-os",64)
    cloud.create_windows_server_2025_vm("brain-win2025",vcpus=2,memory_mb=4096,storage_gb=64,nic="brain-nic")
    evidence=cloud.health_evidence("brain-win2025")
    plan={"location":"emulated","vm_size":"brain-free-small","os_image":"Windows Server 2025","free_only":True}
    return HandoffLedger().issue(evidence,plan)
