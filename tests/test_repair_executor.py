from platform_foundation.repair_executor import BoundedRepairExecutor
from platform_foundation.repair_policy import RepairAction


def test_approved_rerun_is_bounded_and_verified():
    calls = []
    result = BoundedRepairExecutor(max_attempts=2).execute(
        "runner timeout",
        target_sha="abc",
        observed_sha="abc",
        rerun=lambda: calls.append("run") or True,
        verify=lambda: calls.append("verify") or True,
    )
    assert result.attempted is True
    assert result.succeeded is True
    assert result.attempts == 1
    assert result.scope.action is RepairAction.RERUN
    assert calls == ["run", "verify"]


def test_failed_repair_does_not_exceed_bound():
    calls = []
    result = BoundedRepairExecutor(max_attempts=2).execute(
        "runner timeout",
        target_sha="abc",
        observed_sha="abc",
        rerun=lambda: calls.append("run") or False,
        verify=lambda: True,
    )
    assert result.attempted is True
    assert result.succeeded is False
    assert result.attempts == 2
    assert calls == ["run", "run"]


def test_cross_sha_is_blocked_before_callback():
    called = []
    result = BoundedRepairExecutor().execute(
        "runner timeout",
        target_sha="abc",
        observed_sha="def",
        rerun=lambda: called.append("run") or True,
        verify=lambda: True,
    )
    assert result.attempted is False
    assert result.succeeded is False
    assert called == []


def test_unallowlisted_dependency_is_blocked():
    called = []
    result = BoundedRepairExecutor().execute(
        "ModuleNotFoundError: missing package",
        target_sha="abc",
        observed_sha="abc",
        rerun=lambda: called.append("run") or True,
        verify=lambda: True,
    )
    assert result.attempted is False
    assert result.scope.allowed is False
    assert called == []


def test_approved_repair_requires_independent_verifier():
    result = BoundedRepairExecutor().execute(
        "artifact missing",
        target_sha="abc",
        observed_sha="abc",
        rebuild_artifact=lambda: True,
    )
    assert result.attempted is False
    assert result.succeeded is False
    assert result.scope.allowed is False


def test_verifier_failure_consumes_only_bounded_attempts():
    calls = []
    result = BoundedRepairExecutor(max_attempts=2).execute(
        "artifact missing",
        target_sha="abc",
        observed_sha="abc",
        rebuild_artifact=lambda: calls.append("build") or True,
        verify=lambda: calls.append("verify") or False,
    )
    assert result.attempted is True
    assert result.succeeded is False
    assert result.attempts == 2
    assert calls == ["build", "verify", "build", "verify"]
