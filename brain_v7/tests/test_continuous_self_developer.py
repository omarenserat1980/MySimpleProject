from brain_v7.braincore_v2.continuous_self_developer import (
    next_development_cycle,
    promote_cycle,
    supervisor_snapshot,
)


def test_cycles_are_continuous():
    a = next_development_cycle(1)
    b = next_development_cycle(2)
    assert a.task_id != b.task_id


def test_promotion_requires_evidence():
    cycle = next_development_cycle(1)
    assert promote_cycle(cycle, tests_passed=True, evidence="").status == "BLOCKED_NO_EVIDENCE"
    assert promote_cycle(cycle, tests_passed=True, evidence="test-result").status == "PROMOTED"


def test_no_unrestricted_self_modification():
    snap = supervisor_snapshot(10)
    assert snap["continuous_self_development"] is True
    assert snap["unrestricted_self_modification"] is False
