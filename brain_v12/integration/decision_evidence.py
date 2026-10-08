"""Auditable evidence record for Mission Control decisions."""
from dataclasses import dataclass, asdict
import hashlib, json

@dataclass(frozen=True)
class DecisionEvidence:
    mission_fingerprint:str
    action:str
    specialists:tuple[str,...]
    evidence_confidence:float
    external_side_effects:bool
    requires_authorization:bool
    rationale:str

    def canonical(self)->str:
        return json.dumps(asdict(self),sort_keys=True,separators=(",",":"))

    def fingerprint(self)->str:
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

    def valid(self)->bool:
        return (
            len(self.mission_fingerprint)==64
            and self.action in {"HOLD","RESEARCH","ANALYZE","AUTHORIZATION_REQUIRED"}
            and bool(self.specialists)
            and 0.0 <= self.evidence_confidence <= 1.0
            and (not self.external_side_effects or self.requires_authorization)
        )
