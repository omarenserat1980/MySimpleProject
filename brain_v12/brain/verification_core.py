"""Central verification gate: runtime evidence is required for success."""
from __future__ import annotations
from dataclasses import dataclass
from .brain_constitution import BrainConstitution, ConstitutionViolation
from .evidence_store import EvidenceStore

@dataclass(frozen=True)
class VerificationResult:
    verified: bool
    evidence_ids: tuple[str, ...]
    reasons: tuple[str, ...]

class VerificationCore:
    def __init__(self,evidence_store=None,constitution=None):
        self.evidence=evidence_store or EvidenceStore()
        self.constitution=constitution or BrainConstitution()

    def verify(self,task_id,*,required_kind=None):
        items=self.evidence.for_task(task_id)
        valid=[]; reasons=[]
        for item in items:
            checked=self.evidence.verify_hash(item["evidence_id"])
            if checked.get("ok"): valid.append(item)
        runtime=[x for x in valid if str(x.get("kind","")).lower() not in {"ci","ci_evidence"}]
        if not runtime: reasons.append("RUNTIME_EVIDENCE_MISSING")
        if required_kind and not any(x.get("kind")==required_kind for x in runtime):
            reasons.append("REQUIRED_RUNTIME_EVIDENCE_MISSING")
        return VerificationResult(not reasons,tuple(x["evidence_id"] for x in runtime),tuple(reasons))

    def assert_success(self,task_id,*,required_kind=None):
        result=self.verify(task_id,required_kind=required_kind)
        self.constitution.assert_success_claim(verified=result.verified,evidence_ids=list(result.evidence_ids))
        return result
