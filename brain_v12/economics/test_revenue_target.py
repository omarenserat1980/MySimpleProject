from brain_v12.economics.revenue_target import evaluate_target


def test_target_does_not_create_revenue():
    status = evaluate_target(0.0)
    assert status.target.target_amount == 0.10
    assert status.confirmed_revenue == 0.0
    assert status.remaining == 0.10
    assert status.achieved is False


def test_target_is_achieved_by_confirmed_amount_only():
    status = evaluate_target(0.10)
    assert status.achieved is True
    assert status.remaining == 0.0
