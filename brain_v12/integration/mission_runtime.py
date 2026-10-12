"""Durable mission coordinator: lifecycle + hash chain + canonical evidence."""
from __future__ import annotations
from threading import RLock
from ..brain.evidence_store import EvidenceStore
from .mission_lifecycle import MissionState, can_transition
from .mission_ledger import MissionTransition
from .tamper_evident_ledger import hash_record

class MissionRuntime:
    """Single-writer mission coordinator whose state is reconstructed from evidence."""

    def __init__(self, mission_fingerprint:str, evidence_store:EvidenceStore):
        if not mission_fingerprint:
            raise ValueError("mission_fingerprint required")
        self.mission_fingerprint=mission_fingerprint
        self.evidence=evidence_store
        self._lock=RLock()

    def history(self):
        return self.evidence.for_task(
            "mission:"+self.mission_fingerprint[:16],
            mission_id=self.mission_fingerprint,
            phase=None,
        )

    def state(self)->MissionState:
        records=self.history()
        if not records:
            return MissionState.PLANNED
        return MissionState(records[-1]["payload"]["to_state"])

    def root_hash(self)->str:
        records=self.history()
        return records[-1]["payload"].get("record_hash","GENESIS") if records else "GENESIS"

    def verify_chain(self)->bool:
        records=self.history()
        previous="GENESIS"
        for seq,item in enumerate(records,1):
            p=item["payload"]
            if p.get("sequence") != seq:
                return False
            if p.get("previous_hash") != previous:
                return False
            transition=MissionTransition(
                self.mission_fingerprint,
                MissionState(p["from_state"]),
                MissionState(p["to_state"]),
                p["reason"],
                p.get("evidence_fingerprint",""),
                p.get("actor","brain"),
            )
            if not transition.valid():
                return False
            expected=hash_record(seq,transition,previous)
            if p.get("record_hash") != expected:
                return False
            previous=expected
        return True

    def transition(self,to_state:MissionState,reason:str,evidence_fingerprint:str="",actor:str="brain"):
        with self._lock:
            if not self.verify_chain():
                raise RuntimeError("mission evidence chain is invalid")
            current=self.state()
            if not can_transition(current,to_state):
                raise ValueError(f"invalid mission transition: {current.value} -> {to_state.value}")
            transition=MissionTransition(
                self.mission_fingerprint,current,to_state,reason,evidence_fingerprint,actor
            )
            sequence=len(self.history())+1
            previous=self.root_hash()
            record_hash=hash_record(sequence,transition,previous)
            payload={
                "sequence":sequence,
                "mission_fingerprint":self.mission_fingerprint,
                "from_state":current.value,
                "to_state":to_state.value,
                "reason":reason,
                "evidence_fingerprint":evidence_fingerprint,
                "actor":actor,
                "previous_hash":previous,
                "record_hash":record_hash,
            }
            item=self.evidence.append(
                task_id="mission:"+self.mission_fingerprint[:16],
                kind="mission_transition",
                payload=payload,
                producer=actor,
                mission_id=self.mission_fingerprint,
                phase=to_state.value,
            )
            if not self.verify_chain():
                raise RuntimeError("mission transition failed post-write verification")
            return item
