import pytest
from brain_v12.integration.mission_ledger import MissionLedger
from brain_v12.integration.mission_lifecycle import MissionState

def test_ledger_records_ordered_history():
    l=MissionLedger("a"*64)
    l.move(MissionState.ANALYZING,"evidence sufficient")
    l.move(MissionState.EXECUTING,"authorized")
    l.move(MissionState.VERIFYING,"execution finished")
    l.move(MissionState.VERIFIED,"verification passed", "b"*64)
    assert l.state is MissionState.VERIFIED
    assert len(l.history)==4
    assert l.history[-1].evidence_fingerprint=="b"*64

def test_ledger_rejects_invalid_transition():
    l=MissionLedger("a"*64)
    with pytest.raises(ValueError):
        l.move(MissionState.EXECUTING,"skip gates")

def test_verified_cannot_move():
    l=MissionLedger("a"*64)
    l.move(MissionState.ANALYZING,"ok")
    l.move(MissionState.EXECUTING,"authorized")
    l.move(MissionState.VERIFYING,"done")
    l.move(MissionState.VERIFIED,"passed")
    with pytest.raises(ValueError):
        l.move(MissionState.EXECUTING,"retry")
