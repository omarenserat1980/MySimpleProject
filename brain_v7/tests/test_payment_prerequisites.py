from brain_v7.braincore_v2.payment_prerequisites import PaymentPrerequisites


def test_1000_usd_requires_all_prerequisites():
    ok, blockers = PaymentPrerequisites(False, None, False, False).validate_for_1000_usd()
    assert not ok
    assert set(blockers) == {
        "PAYMENT_PROVIDER_NOT_CONNECTED",
        "BALANCE_UNKNOWN",
        "RECIPIENT_NOT_VERIFIED",
        "EXPLICIT_AUTHORIZATION_REQUIRED",
    }


def test_sufficient_balance_and_verified_prerequisites_are_ready():
    p = PaymentPrerequisites(True, 1500, True, True)
    ok, blockers = p.validate_for_1000_usd()
    assert ok
    assert blockers == ()


def test_provider_confirmation_is_required():
    p = PaymentPrerequisites(True, 1500, True, True, "ref-1", "PENDING")
    assert p.reconcile_provider_result(1000) == (False, "PROVIDER_PENDING")


def test_confirmed_provider_result_reconciles():
    p = PaymentPrerequisites(True, 1500, True, True, "ref-1", "CONFIRMED")
    assert p.reconcile_provider_result(1000) == (True, "PROVIDER_CONFIRMED")


def test_amount_mismatch_fails_closed():
    p = PaymentPrerequisites(True, 1500, True, True, "ref-1", "CONFIRMED")
    assert p.reconcile_provider_result(999) == (False, "AMOUNT_MISMATCH")
