from brain_v7.braincore_v2.zero_touch_controller import (
    build_zero_touch_plan,
    can_execute_locally,
    can_record_payment,
    can_submit_externally,
)


def test_local_work_is_zero_touch():
    assert can_execute_locally()
    plan = build_zero_touch_plan("reach first 100000 USD")
    assert plan["mode"] == "ZERO_TOUCH_LOCAL"
    assert plan["fully_autonomous"] is False
    assert plan["submission_gate"] is True


def test_external_submission_needs_authorization():
    assert can_submit_externally(authorized=False) is False
    assert can_submit_externally(authorized=True) is True


def test_payment_needs_provider_confirmation():
    assert can_record_payment(provider_confirmed=False) is False
    assert can_record_payment(provider_confirmed=True) is True
