from platform_foundation.repair_cycle import BoundedRepairCycle


def test_cycle_repairs_and_independently_verifies():
    calls = {"repair": 0, "verify": 0}

    def repair():
        calls["repair"] += 1
        return True

    def verify():
        calls["verify"] += 1
        return True

    result = BoundedRepairCycle().run(
        {"sha": "abc", "error": "runner timeout"},
        target_sha="abc",
        rerun=repair,
        verify=verify,
    )

    assert result.succeeded is True
    assert calls == {"repair": 1, "verify": 1}
    assert result.evidence.allowed is True
    assert result.evidence.attempted is True
    assert result.evidence.succeeded is True
    assert result.evidence.attempts == 1


def test_cycle_blocks_cross_sha_before_repair():
    called = {"repair": False}

    def repair():
        called["repair"] = True
        return True

    result = BoundedRepairCycle().run(
        {"sha": "other", "error": "runner timeout"},
        target_sha="target",
        rerun=repair,
        verify=lambda: True,
    )

    assert result.succeeded is False
    assert called["repair"] is False
    assert result.evidence.allowed is False
    assert result.evidence.attempted is False


def test_cycle_never_claims_success_without_verification():
    result = BoundedRepairCycle().run(
        {"sha": "abc", "error": "runner timeout"},
        target_sha="abc",
        rerun=lambda: True,
        verify=None,
    )

    assert result.succeeded is False
    assert result.evidence.succeeded is False
    assert result.evidence.attempted is False
    assert result.evidence.attempts == 0
