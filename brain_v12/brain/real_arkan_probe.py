"""Minimal, non-destructive real-Arkan probe contract.

This module validates externally supplied real evidence. It never starts a VM,
PowerShell session, or remote command itself.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

@dataclass(frozen=True)
class RealArkanProbe:
    heartbeat: str
    task_evidence: bool
    verification: str
    evidence_hash: str

class RealArkanProbeValidator:
    def validate(self, evidence: dict[str, Any]) -> RealArkanProbe:
        required=("device_id","heartbeat_at","task_id","task_evidence","verification")
        missing=[k for k in required if k not in evidence]
        if missing:
            raise ValueError("MISSING_REAL_EVIDENCE:"+",".join(missing))
        if evidence.get("reality") != "REAL":
            raise ValueError("REALITY_MUST_BE_REAL")
        if evidence.get("heartbeat") != "FRESH":
            raise ValueError("FRESH_REAL_HEARTBEAT_REQUIRED")
        if evidence.get("task_evidence") is not True:
            raise ValueError("REAL_TASK_EVIDENCE_REQUIRED")
        if evidence.get("verification") != "VERIFIED":
            raise ValueError("INDEPENDENT_VERIFICATION_REQUIRED")
        canonical=repr(sorted(evidence.items())).encode()
        return RealArkanProbe("FRESH",True,"VERIFIED",sha256(canonical).hexdigest())
