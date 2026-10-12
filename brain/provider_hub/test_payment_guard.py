from brain.provider_hub.payment_guard import PaymentIdempotencyGuard, PaymentIntent


def intent(key="k1", amount=4900):
    return PaymentIntent("order-1", key, "provider-a", amount, "USD")


def test_first_registration_is_accepted():
    g = PaymentIdempotencyGuard()
    assert g.register(intent()) is True


def test_exact_duplicate_is_rejected_without_side_effect():
    g = PaymentIdempotencyGuard()
    first = intent()
    assert g.register(first) is True
    assert g.register(first) is False
    assert g.lookup("k1") == first


def test_key_reuse_with_changed_amount_is_blocked():
    g = PaymentIdempotencyGuard()
    g.register(intent())
    try:
        g.register(intent(amount=9900))
    except ValueError as exc:
        assert str(exc) == "IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_INTENT"
    else:
        raise AssertionError("unsafe key reuse accepted")
