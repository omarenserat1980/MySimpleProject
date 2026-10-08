"""Tamper-evident hash chain for the mission transition ledger."""
from dataclasses import dataclass
import hashlib, json
from .mission_ledger import MissionTransition

@dataclass(frozen=True)
class LedgerRecord:
    sequence:int
    transition:MissionTransition
    previous_hash:str
    record_hash:str

def hash_record(sequence:int, transition:MissionTransition, previous_hash:str)->str:
    payload={
        "sequence":sequence,
        "mission_fingerprint":transition.mission_fingerprint,
        "from_state":transition.from_state.value,
        "to_state":transition.to_state.value,
        "reason":transition.reason,
        "evidence_fingerprint":transition.evidence_fingerprint,
        "actor":transition.actor,
        "previous_hash":previous_hash,
    }
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(canonical.encode()).hexdigest()

class TamperEvidentLedger:
    def __init__(self):
        self._records=[]

    def append(self, transition:MissionTransition)->LedgerRecord:
        if not transition.valid():
            raise ValueError("invalid transition")
        previous=self._records[-1].record_hash if self._records else "GENESIS"
        sequence=len(self._records)+1
        record_hash=hash_record(sequence,transition,previous)
        record=LedgerRecord(sequence,transition,previous,record_hash)
        self._records.append(record)
        return record

    @property
    def records(self)->tuple[LedgerRecord,...]:
        return tuple(self._records)

    def verify(self)->bool:
        previous="GENESIS"
        for expected_sequence,record in enumerate(self._records,1):
            if record.sequence != expected_sequence or record.previous_hash != previous:
                return False
            if hash_record(record.sequence,record.transition,record.previous_hash) != record.record_hash:
                return False
            previous=record.record_hash
        return True

    def root_hash(self)->str:
        return self._records[-1].record_hash if self._records else "GENESIS"
