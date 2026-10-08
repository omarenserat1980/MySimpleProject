from __future__ import annotations
from .models import EvidenceLevel
from .engine import QuranicResearchEngine

class ScientificEvidenceAdapter:
    """Creates explicitly scientific evidence records; it does not manufacture evidence."""
    def __init__(self, engine: QuranicResearchEngine | None = None):
        self.engine = engine or QuranicResearchEngine()

    def record(self, source: str, claim: str, citation: str,
               confidence: float, metadata: dict | None = None):
        return self.engine.make_evidence(
            EvidenceLevel.SCIENTIFIC, source, claim, citation,
            confidence, metadata or {"present_as": "scientific_evidence"}
        )
