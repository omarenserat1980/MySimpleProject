from platform_foundation import PlatformRuntime


def test_runtime_start_health_and_stop():
    runtime = PlatformRuntime()
    assert not runtime.started
    runtime.start()
    report = runtime.health()
    assert report.passed
    runtime.stop()
    assert not runtime.started


def test_state_snapshot_and_restore():
    runtime = PlatformRuntime()
    runtime.state.set("phase", "foundation")
    snapshot = runtime.state.snapshot()
    runtime.state.set("phase", "changed")
    runtime.state.restore(snapshot)
    assert runtime.state.get("phase") == "foundation"


def test_job_success_and_failure_are_evidenced():
    runtime = PlatformRuntime()
    runtime.start()
    runtime.register_job("ok", lambda: "done")
    runtime.register_job("bad", lambda: 1 / 0)
    assert runtime.run_job("ok").status == "SUCCESS"
    assert runtime.run_job("bad").status == "FAILED"
    events = runtime.evidence.events()
    assert any(e["event"] == "job.success" for e in events)
    assert any(e["event"] == "job.failed" for e in events)


def test_missing_job_is_not_fake_success():
    runtime = PlatformRuntime()
    runtime.start()
    result = runtime.run_job("missing")
    assert result.status == "FAILED"
    assert result.error == "job not found"


def test_foundation_does_not_import_brain():
    source = open("platform_foundation/runtime.py", encoding="utf-8").read()
    assert "import brain_v12" not in source
    assert "from brain_v12" not in source
