from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable
from .models import EvidenceRecord

@dataclass(frozen=True)
class ProvenanceManifest:
    manifest_id: str
    evidence_ids: tuple[str, ...]
    evidence_hash: str
    levels: tuple[str, ...]
    complete: bool
    missing_citations: tuple[str, ...]

class ProvenanceEngine:
    """Build deterministic, auditable provenance manifests; never invent citations."""
    def build(self, evidence: Iterable[EvidenceRecord]) -> ProvenanceManifest:
        records=list(evidence)
        ordered=sorted(records,key=lambda x:x.id)
        payload="\n".join(
            f"{e.id}|{e.level.value}|{e.source}|{e.claim}|{e.citation or ''}"
            for e in ordered
        )
        digest=sha256(payload.encode()).hexdigest()
        missing=tuple(e.id for e in ordered if e.level.value=="L0_QURAN_TEXT" and not e.citation)
        levels=tuple(dict.fromkeys(e.level.value for e in ordered))
        mid=sha256(("PROVENANCE|"+digest).encode()).hexdigest()[:20]
        return ProvenanceManifest(mid,tuple(e.id for e in ordered),digest,levels,
                                  not bool(missing),missing)
