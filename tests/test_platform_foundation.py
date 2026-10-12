from platform_foundation import PlatformRuntime
from platform_foundation.audit import EvidenceLedger
from platform_foundation.failure import FailureKind, FailureTracker
from platform_foundation.recovery import StateCheckpoint
from platform_foundation.security import PermissionPolicy
import pytest


def test_runtime_start_health_and_stop():
    runtime = PlatformRuntime()
    assert not runtime.started
    assert not runtime.health().passed
    runtime.start()
    report = runtime.health()
    assert report.passed
    assert report.checks == {
        "runtime_started": True,
        "state_store": True,
        "evidence_ledger": True,
        "permission_policy": True,
        "failure_tracker": True,
        "recovery_manager": True,
    }
    runtime.stop()
    assert not runtime.started
    assert not runtime.health().passed


def test_state_snapshot_and_restore_isolated():
    runtime = PlatformRuntime()
    runtime.state.set("phase", {"name": "foundation"})
    snapshot = runtime.state.snapshot()
    runtime.state.set("phase", {"name": "changed"})
    runtime.state.restore(snapshot)
    assert runtime.state.get("phase") == {"name": "foundation"}
    snapshot["phase"]["name"] = "external mutation"
    assert runtime.state.get("phase") == {"name": "foundation"}


def test_job_success_and_failure_are_evidenced():
    runtime = PlatformRuntime()
    runtime.start()
    runtime.register_job("ok", lambda: "done")
    runtime.register_job("bad", lambda: 1 / 0)
    assert runtime.run_job("ok").status == "SUCCESS"
    failed = runtime.run_job("bad")
    assert failed.status == "FAILED"
    assert "ZeroDivisionError" in failed.error
    assert runtime.failures.records()[0]["kind"] == FailureKind.INTERNAL.value
    events = runtime.evidence.events()
    assert any(e["event"] == "job.success" for e in events)
    assert any(e["event"] == "job.failed" for e in events)


def test_missing_job_is_not_fake_success():
    runtime = PlatformRuntime()
    runtime.start()
    result = runtime.run_job("missing")
    assert result.status == "FAILED"
    assert result.error == "job not found"


def test_job_cannot_run_before_start():
    runtime = PlatformRuntime()
    runtime.register_job("ok", lambda: "done")
    with pytest.raises(RuntimeError, match="not started"):
        runtime.run_job("ok")


def test_duplicate_or_invalid_job_registration_rejected():
    runtime = PlatformRuntime()
    with pytest.raises(ValueError):
        runtime.register_job("", lambda: None)
    with pytest.raises(ValueError):
        runtime.register_job("not-callable", None)
    with pytest.raises(ValueError):
        runtime.register_job("blank-permission", lambda: None, " ")
    runtime.register_job("one", lambda: 1)
    with pytest.raises(ValueError, match="already registered"):
        runtime.register_job("one", lambda: 2)


def test_evidence_ledger_is_ordered_and_defensive():
    ledger = EvidenceLedger()
    payload = {"nested": {"value": 1}}
    first = ledger.record("first", payload)
    payload["nested"]["value"] = 99
    events = ledger.events()
    assert first.sequence == 1
    assert events[0]["payload"]["nested"]["value"] == 1
    events[0]["payload"]["nested"]["value"] = 42
    assert ledger.events()[0]["payload"]["nested"]["value"] == 1
    assert ledger.record("second", {}).sequence == 2


def test_permission_required_job_denied_by_default_and_allowed_after_grant():
    runtime = PlatformRuntime()
    runtime.start()
    calls = []
    runtime.register_job("publish", lambda: calls.append("ran") or "published", "media.publish")
    denied = runtime.run_job("publish", actor="worker-1")
    assert denied.status == "DENIED"
    assert calls == []
    assert any(e["event"] == "job.denied" for e in runtime.evidence.events())
    runtime.permissions.grant("media.publish", "worker-1", "approved test grant")
    assert runtime.run_job("publish", actor="worker-1").status == "SUCCESS"
    assert calls == ["ran"]


def test_permission_policy_denies_by_default_and_supports_revoke():
    policy = PermissionPolicy()
    assert not policy.is_allowed("system.delete", "worker")
    with pytest.raises(PermissionError):
        policy.require("system.delete", "worker")
    policy.grant("system.delete", "worker", "unit test")
    policy.require("system.delete", "worker")
    assert policy.revoke("system.delete", "worker")
    assert not policy.is_allowed("system.delete", "worker")
    with pytest.raises(ValueError):
        policy.grant("", "worker", "reason")


def test_failure_tracker_classifies_conservatively_without_retrying():
    tracker = FailureTracker()
    transient = tracker.record("network", TimeoutError("timeout"))
    denied = tracker.record("protected", PermissionError("denied"))
    invalid = tracker.record("input", ValueError("invalid"))
    internal = tracker.record("bug", RuntimeError("bug"))
    assert (transient.kind, transient.retryable) == (FailureKind.TRANSIENT.value, True)
    assert (denied.kind, denied.retryable) == (FailureKind.PERMISSION.value, False)
    assert (invalid.kind, invalid.retryable) == (FailureKind.INPUT.value, False)
    assert (internal.kind, internal.retryable) == (FailureKind.INTERNAL.value, False)
    assert [r["sequence"] for r in tracker.records()] == [1, 2, 3, 4]


def test_recovery_checkpoint_restores_state_and_records_evidence():
    runtime = PlatformRuntime()
    runtime.state.set("settings", {"mode": "safe"})
    checkpoint = runtime.recovery.checkpoint()
    runtime.state.set("settings", {"mode": "changed"})
    runtime.recovery.restore(checkpoint)
    assert runtime.state.get("settings") == {"mode": "safe"}
    assert any(e["event"] == "recovery.checkpoint" for e in runtime.evidence.events())
    assert any(e["event"] == "recovery.restore" for e in runtime.evidence.events())


def test_recovery_rejects_tampered_checkpoint():
    runtime = PlatformRuntime()
    runtime.state.set("count", 1)
    checkpoint = runtime.recovery.checkpoint()
    tampered = StateCheckpoint(
        checkpoint_id=checkpoint.checkpoint_id,
        created_at=checkpoint.created_at,
        state={"count": 999},
        sha256=checkpoint.sha256,
    )
    with pytest.raises(ValueError, match="integrity"):
        runtime.recovery.restore(tampered)
    assert runtime.state.get("count") == 1
    assert any(e["event"] == "recovery.restore_rejected" for e in runtime.evidence.events())


def test_recovery_rejects_non_json_state_without_claiming_checkpoint():
    runtime = PlatformRuntime()
    runtime.state.set("not_json", object())
    with pytest.raises(TypeError, match="JSON-compatible"):
        runtime.recovery.checkpoint()


def test_foundation_does_not_import_brain():
    from pathlib import Path
    for path in Path("platform_foundation").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "import brain_v12" not in source
        assert "from brain_v12" not in source
