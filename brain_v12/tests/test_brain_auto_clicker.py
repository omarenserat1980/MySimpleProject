import pytest

from brain_v12.brain.brain_auto_clicker import (
    AutoClickerError, AutoClickPolicy, BrainAutoClicker, ClickTarget,
)


def setup_clicker():
    target = ClickTarget("safe-next", "Next", 10, 20)
    policy = AutoClickPolicy(enabled=True, max_clicks_per_task=2,
                             allowed_target_ids={"safe-next"})
    return BrainAutoClicker(policy), target


def test_disabled_by_default():
    clicker = BrainAutoClicker(AutoClickPolicy())
    target = ClickTarget("safe-next", "Next", 1, 2)
    with pytest.raises(AutoClickerError, match="AUTO_CLICKER_DISABLED"):
        clicker.execute_one(target, click_adapter=lambda _: None,
                            verify_adapter=lambda _: True)


def test_allowlisted_click_requires_postcondition_verification():
    clicker, target = setup_clicker()
    result = clicker.execute_one(target, click_adapter=lambda _: None,
                                 verify_adapter=lambda _: True)
    assert result["status"] == "verified"
    assert result["result_verified"] is True
    assert result["real_device_execution"] is False


def test_failed_verification_disables_further_clicks():
    clicker, target = setup_clicker()
    result = clicker.execute_one(target, click_adapter=lambda _: None,
                                 verify_adapter=lambda _: False)
    assert result["status"] == "verification_failed"
    with pytest.raises(AutoClickerError, match="AUTO_CLICKER_DISABLED"):
        clicker.execute_one(target, click_adapter=lambda _: None,
                            verify_adapter=lambda _: True)


def test_sensitive_target_needs_explicit_approval():
    clicker = BrainAutoClicker(AutoClickPolicy(
        enabled=True, allowed_target_ids={"pay-button"}))
    target = ClickTarget("pay-button", "Pay now", 5, 5)
    with pytest.raises(AutoClickerError, match="SENSITIVE_ACTION_APPROVAL_REQUIRED"):
        clicker.execute_one(target, click_adapter=lambda _: None,
                            verify_adapter=lambda _: True)


def test_non_allowlisted_target_is_rejected():
    clicker, target = setup_clicker()
    unsafe = ClickTarget("unknown", "Next", 1, 1)
    with pytest.raises(AutoClickerError, match="TARGET_NOT_ALLOWLISTED"):
        clicker.execute_one(unsafe, click_adapter=lambda _: None,
                            verify_adapter=lambda _: True)


def test_emergency_stop_blocks_clicks():
    clicker, target = setup_clicker()
    clicker.stop()
    with pytest.raises(AutoClickerError, match="EMERGENCY_STOP_ACTIVE"):
        clicker.execute_one(target, click_adapter=lambda _: None,
                            verify_adapter=lambda _: True)


def test_task_click_limit_is_enforced():
    clicker, target = setup_clicker()
    clicker.execute_one(target, click_adapter=lambda _: None,
                        verify_adapter=lambda _: True)
    clicker.execute_one(target, click_adapter=lambda _: None,
                        verify_adapter=lambda _: True)
    with pytest.raises(AutoClickerError, match="TASK_CLICK_LIMIT_REACHED"):
        clicker.execute_one(target, click_adapter=lambda _: None,
                            verify_adapter=lambda _: True)
