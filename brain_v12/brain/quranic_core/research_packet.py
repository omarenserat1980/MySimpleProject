from __future__ import annotations
from hashlib import sha256
from .models import QuranicFinding
from .publication import PublicationGate

class ResearchPacketBuilder:
    """Create an auditable, non-publishing research packet."""
    def __init__(self, gate=None):
        self.gate=gate or PublicationGate()

    def build(self,finding: QuranicFinding) -> dict:
        decision=self.gate.evaluate(finding)
        packet={
            "packet_version":"1.0",
            "question":finding.question,
            "finding":finding.finding,
            "evidence":[e.__dict__ | {"level":e.level.value} for e in finding.evidence],
            "limitations":list(finding.limitations),
            "alternatives":list(finding.alternatives),
            "decision":decision,
        }
        canonical=str(packet).encode()
        packet["packet_id"]=sha256(canonical).hexdigest()[:24]
        packet["publishable"]=False
        return packet
