"""Strict lifecycle state machine for Brain missions."""
from enum import Enum

class MissionState(str,Enum):
    PLANNED="PLANNED"
    RESEARCHING="RESEARCHING"
    ANALYZING="ANALYZING"
    AUTHORIZATION_REQUIRED="AUTHORIZATION_REQUIRED"
    EXECUTING="EXECUTING"
    VERIFYING="VERIFYING"
    VERIFIED="VERIFIED"
    REJECTED="REJECTED"
    HOLD="HOLD"

_TRANSITIONS={
    MissionState.PLANNED:{MissionState.RESEARCHING,MissionState.ANALYZING,MissionState.AUTHORIZATION_REQUIRED,MissionState.HOLD},
    MissionState.RESEARCHING:{MissionState.ANALYZING,MissionState.HOLD,MissionState.REJECTED},
    MissionState.ANALYZING:{MissionState.AUTHORIZATION_REQUIRED,MissionState.EXECUTING,MissionState.HOLD,MissionState.REJECTED},
    MissionState.AUTHORIZATION_REQUIRED:{MissionState.EXECUTING,MissionState.HOLD,MissionState.REJECTED},
    MissionState.EXECUTING:{MissionState.VERIFYING,MissionState.REJECTED},
    MissionState.VERIFYING:{MissionState.VERIFIED,MissionState.REJECTED},
    MissionState.VERIFIED:set(),
    MissionState.REJECTED:set(),
    MissionState.HOLD:{MissionState.RESEARCHING,MissionState.PLANNED,MissionState.REJECTED},
}

def can_transition(current:MissionState,next_state:MissionState)->bool:
    return next_state in _TRANSITIONS.get(current,set())

def transition(current:MissionState,next_state:MissionState)->MissionState:
    if not can_transition(current,next_state):
        raise ValueError(f"invalid mission transition: {current.value} -> {next_state.value}")
    return next_state
