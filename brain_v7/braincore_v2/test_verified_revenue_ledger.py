from brain_v7.braincore_v2.verified_revenue_ledger import VerifiedRevenueLedger


def test_revenue_is_idempotent():
    ledger = VerifiedRevenueLedger()
    first = ledger.record(
        source="test",
        external_id="ORDER-1",
        amount_jod=25,
        evidence="provider payment reference",
        recorded_at=1,
    )
    second = ledger.record(
        source="test",
        external_id="ORDER-1",
        amount_jod=25,
        evidence="provider payment reference",
        recorded_at=2,
    )
    assert first["status"] == "RECORDED"
    assert second["status"] == "DUPLICATE_IGNORED"
    assert ledger.total_jod() == 25
