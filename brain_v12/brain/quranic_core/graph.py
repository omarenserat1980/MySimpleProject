from __future__ import annotations
from dataclasses import dataclass,asdict
from hashlib import sha256
from typing import Iterable
from .models import EvidenceRecord,QuranicFinding

@dataclass(frozen=True)
class GraphNode:
    id:str
    kind:str
    label:str
    evidence_id:str|None=None

@dataclass(frozen=True)
class GraphEdge:
    source:str
    relation:str
    target:str

class EvidenceGraph:
    def build(self,finding:QuranicFinding)->dict:
        nodes=[GraphNode("question","question",finding.question),
               GraphNode("finding","finding",finding.finding)]
        edges=[GraphEdge("question","supports","finding")]
        for e in finding.evidence:
            nodes.append(GraphNode("evidence:"+e.id,e.level.value,e.claim,e.id))
            edges.append(GraphEdge("evidence:"+e.id,"supports","finding"))
            relation=str(e.metadata.get("relation","supports"))
            if relation in {"counter","opposing","contradictory"}:
                edges[-1]=GraphEdge("evidence:"+e.id,relation,"finding")
        payload="|".join(n.id+n.kind+n.label for n in nodes)+"||"+"|".join(asdict(x).__repr__() for x in edges)
        return {"graph_id":sha256(payload.encode()).hexdigest()[:20],
                "nodes":[asdict(x) for x in nodes],"edges":[asdict(x) for x in edges],
                "counter_evidence":[e.id for e in finding.evidence if e.metadata.get("relation") in {"counter","opposing","contradictory"}]}
