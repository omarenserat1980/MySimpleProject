"""Auditable mission transition ledger."""
from dataclasses import dataclass
from datetime import datetime, timezone
from .mission_lifecycle import MissionState, can_transition

@dataclass(frozen=True)
class MissionTransition:
    mission_fingerprint: str
    from_state: MissionState
    to_state: MissionState
    reason: str
    evidence_fingerprint: str = ""
    actor: str = "brain"

    def valid(self)->bool:
        return (
            bool(self.mission_fingerprint)
            and can_transition(self.from_state,self.to_state)
            and bool(self.reason)
            and bool(self.actor)
        )

class MissionLedger:
    def __init__(self, mission_fingerprint:str):
        if not mission_fingerprint:
            raise ValueError("mission_fingerprint required")
        self.mission_fingerprint=mission_fingerprint
        self._state=MissionState.PLANNED
        self._history=[]

    @property
    def state(self)->MissionState:
        return self._state

    @property
    def history(self)->tuple[MissionTransition,...]:
        return tuple(self._history)

    def move(self,to_state:MissionState,reason:str,evidence_fingerprint:str="",actor:str="brain")->MissionTransition:
        event=MissionTransition(self.mission_fingerprint,self._state,to_state,reason,evidence_fingerprint,actor)
        if not event.valid():
            raise ValueError(f"invalid mission transition: {self._state.value} -> {to_state.value}")
        self._history.append(event)
        self._state=to_state
        return event
