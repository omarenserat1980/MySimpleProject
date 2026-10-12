import pytest
from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.integration.mission_runtime import MissionRuntime
from brain_v12.integration.mission_lifecycle import MissionState

def test_runtime_rebuilds_state_from_evidence(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    r=MissionRuntime("a"*64,store)
    r.transition(MissionState.ANALYZING,"evidence sufficient")
    r.transition(MissionState.EXECUTING,"authorized")
    assert r.state() is MissionState.EXECUTING
    assert r.verify_chain()
    assert len(r.history())==2

def test_runtime_survives_new_instance(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    r=MissionRuntime("a"*64,store)
    r.transition(MissionState.ANALYZING,"evidence")
    r2=MissionRuntime("a"*64,store)
    assert r2.state() is MissionState.ANALYZING
    assert r2.verify_chain()

def test_runtime_rejects_illegal_transition(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    r=MissionRuntime("a"*64,store)
    with pytest.raises(ValueError):
        r.transition(MissionState.EXECUTING,"skip")

def test_runtime_detects_tampering(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    r=MissionRuntime("a"*64,store)
    item=r.transition(MissionState.ANALYZING,"evidence")
    store.db.execute("UPDATE evidence SET payload=? WHERE evidence_id=?",('{"tampered":true}',item["evidence_id"]))
    store.db.commit()
    assert not r.verify_chain()
    with pytest.raises(RuntimeError):
        r.transition(MissionState.HOLD,"blocked")
