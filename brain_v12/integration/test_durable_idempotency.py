from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.integration.idempotency_gate import ExecutionIntent
from brain_v12.integration.durable_idempotency import DurableIdempotencyGate

def test_idempotency_survives_new_gate_instance(tmp_path):
    store=EvidenceStore(tmp_path/"e.db")
    i=ExecutionIntent("a"*64,"publish","p"*64)
    g=DurableIdempotencyGate(store)
    assert g.claim(i)["ok"]
    g.complete(i)
    g2=DurableIdempotencyGate(store)
    assert g2.status(i)["status"]=="COMPLETED"
    assert not g2.claim(i)["ok"]

def test_claim_is_persistent(tmp_path):
    store=EvidenceStore(tmp_path/"e.db")
    i=ExecutionIntent("a"*64,"publish","p"*64)
    assert DurableIdempotencyGate(store).claim(i)["ok"]
    assert DurableIdempotencyGate(store).claim(i)["ok"] is False
