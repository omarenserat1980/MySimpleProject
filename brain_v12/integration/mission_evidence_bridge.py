"""Persistence bridge from the Mission Ledger into Brain's canonical EvidenceStore."""
from dataclasses import asdict
from ..brain.evidence_store import EvidenceStore
from .mission_ledger import MissionTransition

class MissionEvidenceBridge:
    """Persist mission transitions as canonical Brain evidence records."""

    def __init__(self, evidence_store:EvidenceStore):
        self.evidence=evidence_store

    def record_transition(self, transition:MissionTransition):
        if not transition.valid():
            raise ValueError("invalid mission transition")
        payload={
            "mission_fingerprint":transition.mission_fingerprint,
            "from_state":transition.from_state.value,
            "to_state":transition.to_state.value,
            "reason":transition.reason,
            "evidence_fingerprint":transition.evidence_fingerprint,
            "actor":transition.actor,
        }
        return self.evidence.append(
            task_id="mission:"+transition.mission_fingerprint[:16],
            kind="mission_transition",
            payload=payload,
            producer=transition.actor,
            mission_id=transition.mission_fingerprint,
            phase=transition.to_state.value,
        )

    def verify_transition_record(self,evidence_id:str):
        return self.evidence.verify_hash(evidence_id)

    def mission_history(self,mission_fingerprint:str):
        return self.evidence.for_task(
            "mission:"+mission_fingerprint[:16],
            mission_id=mission_fingerprint,
        )
