from brain_v12.integration.mission_lifecycle import MissionState
from brain_v12.integration.mission_ledger import MissionLedger
from brain_v12.integration.tamper_evident_ledger import TamperEvidentLedger

def event():
    l=MissionLedger("a"*64)
    return l.move(MissionState.ANALYZING,"evidence sufficient","b"*64)

def test_chain_is_valid():
    t=TamperEvidentLedger()
    t.append(event())
    assert t.verify()
    assert len(t.root_hash())==64

def test_chain_detects_tampering():
    t=TamperEvidentLedger()
    t.append(event())
    r=t.records[0]
    object.__setattr__(r.transition,"reason","tampered")
    assert not t.verify()

def test_chain_links_records():
    t=TamperEvidentLedger()
    first=event()
    second=MissionLedger("a"*64).move(MissionState.ANALYZING,"next")
    t.append(first)
    # second is independently valid but belongs to same mission; chain still binds sequence
    t.append(second)
    assert t.records[1].previous_hash==t.records[0].record_hash
