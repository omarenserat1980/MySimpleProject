from __future__ import annotations
from .provenance import ProvenanceEngine
from .graph import EvidenceGraph

class PublicationGate:
    def __init__(self):
        self.provenance=ProvenanceEngine()
        self.graph=EvidenceGraph()
    def evaluate(self,finding):
        manifest=self.provenance.build(finding.evidence)
        graph=self.graph.build(finding)
        counter=bool(graph["counter_evidence"])
        if not manifest.complete: status="HOLD"
        elif not counter: status="HOLD"
        else: status="HUMAN_REVIEW"
        return {"status":status,"publish":False,"manifest":manifest.__dict__,
                "graph":graph,"reason":"human review required; Brain does not auto-publish"}
