import pytest
from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.integration.mission_runtime import MissionRuntime
from brain_v12.integration.mission_lifecycle import MissionState
from brain_v12.integration.mission_recovery import inspect,RecoveryStatus

def test_new_mission_is_healthy(tmp_path):
    r=MissionRuntime("a"*64,EvidenceStore(tmp_path/"e.db"))
    x=inspect(r)
    assert x.status==RecoveryStatus.HEALTHY
    assert x.state is MissionState.PLANNED

def test_interrupted_execution_is_recoverable(tmp_path):
    r=MissionRuntime("a"*64,EvidenceStore(tmp_path/"e.db"))
    r.transition(MissionState.ANALYZING,"ready")
    r.transition(MissionState.EXECUTING,"authorized")
    x=inspect(r)
    assert x.status==RecoveryStatus.RECOVERABLE
    assert x.state is MissionState.EXECUTING

def test_corruption_blocks_recovery(tmp_path):
    s=EvidenceStore(tmp_path/"e.db")
    r=MissionRuntime("a"*64,s)
    item=r.transition(MissionState.ANALYZING,"ready")
    s.db.execute("UPDATE evidence SET payload=? WHERE evidence_id=?",('{"corrupt":1}',item["evidence_id"]))
    s.db.commit()
    x=inspect(r)
    assert x.status==RecoveryStatus.CORRUPTED
    assert x.state is MissionState.HOLD
