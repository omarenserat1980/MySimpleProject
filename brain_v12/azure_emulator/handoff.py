from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, time, uuid
from typing import Any
from .service import AzureEmulator

@dataclass(frozen=True)
class HandoffCertificate:
    schema: str
    certificate_id: str
    issued_at: float
    expires_at: float
    evidence_sha256: str
    plan_sha256: str
    provider: str
    vm_id: str
    free_only: bool

def issue_handoff(evidence: dict[str, Any], plan: dict[str, Any], *, ttl_seconds: int = 300) -> dict[str, Any]:
    if not evidence.get("ok"):
        raise RuntimeError("HANDOFF_REQUIRES_VERIFIED_EMULATOR")
    if evidence.get("provider") != "brain-emulated-azure":
        raise RuntimeError("HANDOFF_PROVIDER_INVALID")
    vm = evidence.get("vm") or {}
    props = vm.get("properties") or {}
    if vm.get("state") != "RUNNING" or props.get("os") != "Windows Server 2025" or props.get("architecture") != "x86_64":
        raise RuntimeError("HANDOFF_VM_NOT_VERIFIED")
    if plan.get("free_only") is not True:
        raise RuntimeError("HANDOFF_FREE_ONLY_REQUIRED")
    usage = evidence.get("usage") or {}
    quota = evidence.get("quota") or {}
    if any(int(usage.get(k, 0)) > int(quota.get(k, 0)) for k in ("vcpus","memory_mb","storage_gb")):
        raise RuntimeError("HANDOFF_CAPACITY_INVALID")
    canonical_e = json.dumps(evidence, sort_keys=True, separators=(",",":")).encode()
    canonical_p = json.dumps(plan, sort_keys=True, separators=(",",":")).encode()
    now=time.time()
    return {
        "schema":"BRAIN-REAL-AZURE-HANDOFF-2",
        "certificate_id":str(uuid.uuid4()),
        "issued_at":now,
        "expires_at":now+max(1,min(int(ttl_seconds),3600)),
        "evidence_sha256":hashlib.sha256(canonical_e).hexdigest(),
        "plan_sha256":hashlib.sha256(canonical_p).hexdigest(),
        "provider":"brain-emulated-azure",
        "vm_id":vm.get("id"),
        "free_only":True,
        "single_use":True,
    }

def certify_default_handoff() -> dict[str, Any]:
    cloud=AzureEmulator(free_only=True)
    cloud.create_resource_group("brain-rg")
    cloud.create_network("brain-vnet")
    cloud.create_subnet("brain-subnet","brain-vnet")
    cloud.create_public_ip("brain-ip")
    cloud.create_nic("brain-nic","brain-subnet","brain-ip")
    cloud.create_disk("brain-os",64)
    cloud.create_windows_server_2025_vm("brain-win2025",vcpus=2,memory_mb=4096,storage_gb=64,nic="brain-nic")
    evidence=cloud.health_evidence("brain-win2025")
    plan={"location":"emulated","vm_size":"brain-free-small","os_image":"Windows Server 2025","free_only":True}
    return issue_handoff(evidence,plan)
