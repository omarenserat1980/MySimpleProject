from __future__ import annotations

from platform_foundation.apm import APM
from platform_foundation.persistent_state import SQLiteStateStore


def test_apm_persists_metrics_and_context(tmp_path):
    store = SQLiteStateStore(tmp_path / "apm.db")
    apm = APM(store, clock=lambda: 100.0)
    apm.counter("requests.total", 2, task_id="task-1", run_id="run-1", commit_sha="abc")
    apm.counter("requests.errors", 1, task_id="task-1", run_id="run-1", commit_sha="abc")
    apm.observe("latency.ms", 42, task_id="task-1", run_id="run-1", commit_sha="abc")

    snapshot = apm.snapshot()
    assert len(snapshot) == 3
    assert any(p["metric"] == "requests.total" and p["last_task_id"] == "task-1" for p in snapshot)

    restored = APM(store, clock=lambda: 100.0)
    health = restored.health()
    assert health["status"] == "DEGRADED"
    assert health["error_rate"] == 0.5


def test_apm_does_not_call_missing_telemetry_healthy(tmp_path):
    store = SQLiteStateStore(tmp_path / "apm.db")
    apm = APM(store, clock=lambda: 100.0)
    assert apm.health()["status"] == "UNKNOWN"


def test_apm_detects_stale_telemetry(tmp_path):
    store = SQLiteStateStore(tmp_path / "apm.db")
    apm = APM(store, clock=lambda: 100.0)
    apm.counter("requests.total", 1)
    assert apm.health(now=500.0, max_age_seconds=10)["status"] == "UNKNOWN"


def test_apm_duration_records_elapsed_time(tmp_path):
    now = [1.0]
    store = SQLiteStateStore(tmp_path / "apm.db")
    apm = APM(store, clock=lambda: now[0])
    finish = apm.duration("task.duration_ms", task_id="t1")
    now[0] = 1.125
    point = finish()
    assert point.value == 125.0
    assert apm.snapshot()[0]["metric"] == "task.duration_ms"


def test_apm_enforces_cardinality_and_counter_rules(tmp_path):
    store = SQLiteStateStore(tmp_path / "apm.db")
    apm = APM(store, max_series=1)
    apm.counter("requests.total", 1)
    try:
        apm.counter("requests.total", -1)
        assert False
    except ValueError:
        pass
    try:
        apm.counter("other.total", 1)
        assert False
    except RuntimeError:
        pass
