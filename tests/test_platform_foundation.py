from platform_foundation import PlatformRuntime
from platform_foundation.audit import EvidenceLedger
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
    }
    runtime.stop()
    assert not runtime.started
    assert not runtime.health().passed


def test_state_snapshot_and_restore_isolated():
    runtime = PlatformRuntime()
    runtime.state.set("phase", "foundation")
    snapshot = runtime.state.snapshot()
    runtime.state.set("phase", "changed")
    runtime.state.restore(snapshot)
    assert runtime.state.get("phase") == "foundation"
    snapshot["phase"] = "external mutation"
    assert runtime.state.get("phase") == "foundation"


def test_job_success_and_failure_are_evidenced():
    runtime = PlatformRuntime()
    runtime.start()
    runtime.register_job("ok", lambda: "done")
    runtime.register_job("bad", lambda: 1 / 0)
    assert runtime.run_job("ok").status == "SUCCESS"
    failed = runtime.run_job("bad")
    assert failed.status == "FAILED"
    assert "ZeroDivisionError" in failed.error
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


def test_foundation_does_not_import_brain():
    from pathlib import Path
    for path in Path("platform_foundation").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "import brain_v12" not in source
        assert "from brain_v12" not in source
