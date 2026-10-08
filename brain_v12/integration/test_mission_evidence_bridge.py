from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.integration.mission_ledger import MissionLedger
from brain_v12.integration.mission_lifecycle import MissionState
from brain_v12.integration.mission_evidence_bridge import MissionEvidenceBridge

def test_transition_persists_in_canonical_evidence_store(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    bridge=MissionEvidenceBridge(store)
    ledger=MissionLedger("a"*64)
    transition=ledger.move(MissionState.ANALYZING,"evidence sufficient","b"*64)
    item=bridge.record_transition(transition)
    assert item["kind"]=="mission_transition"
    assert item["mission_id"]=="a"*64
    assert bridge.verify_transition_record(item["evidence_id"])["ok"] is True
    assert len(bridge.mission_history("a"*64))==1

def test_other_mission_is_not_returned(tmp_path):
    store=EvidenceStore(tmp_path/"evidence.db")
    bridge=MissionEvidenceBridge(store)
    a=MissionLedger("a"*64).move(MissionState.ANALYZING,"a")
    b=MissionLedger("b"*64).move(MissionState.ANALYZING,"b")
    bridge.record_transition(a)
    bridge.record_transition(b)
    assert len(bridge.mission_history("a"*64))==1
    assert bridge.mission_history("a"*64)[0]["payload"]["reason"]=="a"
