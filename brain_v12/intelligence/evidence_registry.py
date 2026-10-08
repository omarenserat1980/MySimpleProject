"""Immutable-style evidence records for multidisciplinary analysis."""
from dataclasses import dataclass
import hashlib, json

@dataclass(frozen=True)
class Evidence:
    evidence_id:str
    domain:str
    claim:str
    source_ref:str
    observed_at:str
    confidence:float

    def fingerprint(self)->str:
        payload={"id":self.evidence_id,"domain":self.domain,"claim":self.claim,"source":self.source_ref,"observed_at":self.observed_at,"confidence":self.confidence}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def validate(e:Evidence)->bool:
    return bool(e.evidence_id and e.domain and e.claim and e.source_ref and e.observed_at and 0<=e.confidence<=1)
