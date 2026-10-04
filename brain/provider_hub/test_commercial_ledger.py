from brain.provider_hub.commercial_ledger import CommercialLedger


def test_record_and_filter_order():
    ledger = CommercialLedger()
    entry = ledger.record(
        "l1", "o1", "NEW", "PAYMENT_VERIFIED",
        evidence_refs=("pay-1",),
        provider_id="provider-a",
        amount_minor=4900,
        currency="USD",
    )
    assert entry.order_id == "o1"
    assert ledger.for_order("o1")[0].evidence_refs == ("pay-1",)


def test_duplicate_entry_is_rejected():
    ledger = CommercialLedger()
    ledger.record("l1", "o1", "NEW", "PAYMENT_VERIFIED")
    try:
        ledger.record("l1", "o1", "NEW", "PAYMENT_VERIFIED")
    except ValueError as exc:
        assert str(exc) == "DUPLICATE_LEDGER_ENTRY:l1"
    else:
        raise AssertionError("duplicate ledger entry accepted")


def test_negative_amount_is_rejected():
    ledger = CommercialLedger()
    try:
        ledger.record("l1", "o1", "NEW", "PAYMENT_VERIFIED", amount_minor=-1)
    except ValueError as exc:
        assert str(exc) == "NEGATIVE_AMOUNT"
    else:
        raise AssertionError("negative amount accepted")
