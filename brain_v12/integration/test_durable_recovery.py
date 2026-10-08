from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.integration.idempotency_gate import ExecutionIntent
from brain_v12.integration.durable_recovery import ExecutionRecovery

def test_lease_and_stale_detection(tmp_path):
    s=EvidenceStore(tmp_path/"e.db")
    i=ExecutionIntent("a"*64,"publish","p"*64)
    s.claim_execution(i.execution_key,i.mission_fingerprint,i.action,i.parameters_fingerprint)
    s.db.execute("UPDATE execution_idempotency SET lease_until=0 WHERE execution_key=?",(i.execution_key,))
    s.db.commit()
    assert len(ExecutionRecovery(s).stale())==1

def test_renew_extends_lease(tmp_path):
    s=EvidenceStore(tmp_path/"e.db")
    i=ExecutionIntent("a"*64,"publish","p"*64)
    s.claim_execution(i.execution_key,i.mission_fingerprint,i.action,i.parameters_fingerprint)
    x=ExecutionRecovery(s).renew(i,300)
    assert x["lease_until"] is not None
