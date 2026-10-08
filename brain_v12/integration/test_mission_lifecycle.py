import pytest
from brain_v12.integration.mission_lifecycle import MissionState,can_transition,transition

def test_valid_execution_path():
    states=[MissionState.PLANNED,MissionState.ANALYZING,MissionState.EXECUTING,MissionState.VERIFYING,MissionState.VERIFIED]
    for a,b in zip(states,states[1:]):
        assert can_transition(a,b)
        assert transition(a,b)==b

def test_external_path_requires_authorization():
    assert can_transition(MissionState.ANALYZING,MissionState.AUTHORIZATION_REQUIRED)
    assert can_transition(MissionState.AUTHORIZATION_REQUIRED,MissionState.EXECUTING)

def test_cannot_execute_directly_from_planned():
    assert not can_transition(MissionState.PLANNED,MissionState.EXECUTING)
    with pytest.raises(ValueError):
        transition(MissionState.PLANNED,MissionState.EXECUTING)

def test_verified_is_terminal():
    assert not can_transition(MissionState.VERIFIED,MissionState.EXECUTING)
