from brain_v12.economics.economic_control import CausalChain
from brain_v12.economics.economic_settlement import SettlementEvent, rebuild_ledger
from brain_v12.economics.revenue_gate import PaymentEvidence
from brain_v12.economics.revenue_integrity import verify_payment_evidence


def proof(evidence_id="ev-1", amount=0.10):
    return PaymentEvidence(
        evidence_id=evidence_id,
        opportunity_id="opp-1",
        amount=amount,
        currency="USD",
        received_at="2026-10-08T01:00:00Z",
        proof_ref="payment://verified/1",
    )


def chain(evidence_id="ev-1"):
    return CausalChain("opp-1", "app-1", "task-1", "del-1", evidence_id)


def test_duplicate_evidence_is_rejected():
    e = proof()
    first = verify_payment_evidence(e)
    second = verify_payment_evidence(
        e,
        existing_evidence_ids=[e.evidence_id],
        existing_evidence_hashes=[first.proof.evidence_hash],
    )
    assert first.valid
    assert second.valid is False
    assert second.reason == "DUPLICATE_EVIDENCE_ID"


def test_ledger_rebuild_counts_verified_event_once():
    e = proof()
    checked = verify_payment_evidence(e)
    event = SettlementEvent("rev-1", checked.proof, chain())
    snapshot = rebuild_ledger([event])
    assert snapshot.confirmed_revenue == 0.10
    assert snapshot.event_count == 1


def test_ledger_rejects_duplicate_evidence():
    e1 = proof("ev-1")
    e2 = proof("ev-1", 0.20)
    p1 = verify_payment_evidence(e1).proof
    p2 = verify_payment_evidence(e2).proof
    try:
        rebuild_ledger([
            SettlementEvent("rev-1", p1, chain("ev-1")),
            SettlementEvent("rev-2", p2, chain("ev-1")),
        ])
        assert False
    except ValueError as exc:
        assert "duplicate payment evidence" in str(exc)
