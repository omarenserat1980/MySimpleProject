"""Candidate selection for temporary real-KVM workers.

No provider is hard-coded. The Brain ranks candidate backends and only permits
a candidate whose contract says it can attest real KVM/QEMU. Paid candidates
remain disabled unless explicitly enabled by the caller.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class KVMWorkerOption:
    provider: str
    backend: str
    estimated_cost_usd: float
    supports_kvm: bool
    supports_nested: bool = False
    free_tier: bool = False
    notes: str = ""

def rank_options(options: Iterable[KVMWorkerOption], *, allow_paid: bool=False):
    accepted=[]; rejected=[]
    for x in options:
        if not x.supports_kvm:
            rejected.append((x.provider,"REAL_KVM_UNSUPPORTED"))
        elif x.estimated_cost_usd > 0 and not allow_paid:
            rejected.append((x.provider,"PAID_DISABLED"))
        else:
            accepted.append(x)
    accepted.sort(key=lambda x:(0 if x.free_tier else 1,x.estimated_cost_usd,x.provider))
    return accepted,rejected

def default_options():
    return [
        KVMWorkerOption("brain-owned-executor","dedicated-linux-qemu-kvm",0.0,True,True,True,
                        "Preferred: existing Brain executor/worker contract."),
        KVMWorkerOption("github-actions-self-hosted","self-hosted-linux-kvm",0.0,True,True,True,
                        "Only if a connected self-hosted runner actually exposes /dev/kvm."),
        KVMWorkerOption("azure","temporary-linux-kvm-vm",0.0,True,True,False,
                        "Fallback only; may incur charges and requires explicit cost authorization."),
        KVMWorkerOption("render","container",0.0,False,False,True,
                        "Control-plane hosting only; not a real Windows/KVM executor."),
    ]
