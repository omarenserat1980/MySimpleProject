from __future__ import annotations

import threading
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.parallel_chunks import ParallelChunkRunner
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.lease import TaskLease


def test_chunks_run_with_bounded_parallelism(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)
    active = {"value": 0, "max": 0}
    lock = threading.Lock()

    def execute(chunk, _deps):
        with lock:
            active["value"] += 1
            active["max"] = max(active["max"], active["value"])
        time.sleep(0.05)
        with lock:
            active["value"] -= 1
        return {"chunk": chunk}

    results = runner.run(
        "run-1", ["1", "2", "3", "4"], execute,
        lambda chunk, output: output["chunk"] == chunk,
        max_workers=2,
    )
    assert all(result.status == "SUCCESS" for result in results)
    assert active["max"] == 2
    assert audit.verify()
    store.close()


def test_dependency_layers_parallelize_without_violating_order(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)
    running = set()
    lock = threading.Lock()
    observed = []

    def execute(chunk, deps):
        with lock:
            running.add(chunk)
            observed.append(("start", chunk, sorted(running)))
        time.sleep(0.03)
        if chunk == "C":
            assert "A" in [item[1] for item in observed if item[0] == "done"]
            assert "B" in [item[1] for item in observed if item[0] == "done"]
        with lock:
            running.discard(chunk)
            observed.append(("done", chunk, []))
        return {"chunk": chunk, "deps": sorted(deps)}

    results = runner.run(
        "run-deps",
        ["A", "B", "C", "D"],
        execute,
        lambda _chunk, output: True,
        dependencies={"C": ["A", "B"], "D": ["B"]},
        max_workers=2,
    )
    assert all(result.status == "SUCCESS" for result in results)
    c = next(result for result in results if result.chunk_id == "C")
    assert c.output["deps"] == ["A", "B"]
    store.close()


def test_dependency_cycle_is_rejected_before_execution(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)
    calls = []
    try:
        runner.run(
            "cycle", ["A", "B"], lambda chunk, deps: calls.append(chunk),
            lambda _chunk, _output: True,
            dependencies={"A": ["B"], "B": ["A"]},
        )
        assert False
    except ValueError as exc:
        assert "cycle" in str(exc)
    assert calls == []
    store.close()


def test_restart_resumes_only_unfinished_chunks(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStateStore(path)
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)

    def first(chunk, _deps):
        if chunk == "3":
            raise RuntimeError("temporary")
        return chunk

    first_results = runner.run(
        "run-2", ["1", "2", "3"], first,
        lambda _chunk, output: output in {"1", "2"},
        max_workers=2,
    )
    assert [r.status for r in first_results] == ["SUCCESS", "SUCCESS", "FAILED"]
    store.close()

    reopened = SQLiteStateStore(path)
    resumed = ParallelChunkRunner(reopened, audit)
    resumed_calls = []
    second_results = resumed.run(
        "run-2", ["1", "2", "3"],
        lambda chunk, _deps: resumed_calls.append(chunk) or chunk,
        lambda _chunk, _output: True,
        max_workers=2,
    )
    assert [r.status for r in second_results] == ["SUCCESS", "SUCCESS", "SUCCESS"]
    assert resumed_calls == ["3"]
    reopened.close()


def test_failed_chunk_never_becomes_success_without_verification(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)
    results = runner.run(
        "run-3", ["bad"], lambda _chunk, _deps: "output",
        lambda _chunk, _output: False, max_workers=1,
    )
    assert results[0].status == "FAILED"
    assert store.get("pipeline.chunk:run-3:bad")["status"] == "FAILED"
    assert audit.verify()
    store.close()


def test_concurrent_chunk_owner_is_fenced(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    lease = TaskLease(store, audit)
    assert lease.acquire("run-lease:A", "other-worker", ttl_seconds=60).acquired
    runner = ParallelChunkRunner(store, audit, lease=lease)

    results = runner.run(
        "run-lease", ["A"], lambda chunk, _deps: chunk,
        lambda _chunk, _output: True, max_workers=1,
    )
    assert results[0].status == "FAILED"
    assert "lease" in (results[0].error or "")
    assert store.get("pipeline.chunk:run-lease:A") is None
    store.close()


def test_chunk_cannot_commit_after_lease_expiry(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)

    def execute(chunk, _deps):
        time.sleep(0.03)
        return chunk

    results = runner.run(
        "run-fence", ["A"], execute,
        lambda _chunk, _output: True,
        max_workers=1, lease_ttl_seconds=0.01,
    )
    assert results[0].status == "FAILED"
    assert "lease lost" in (results[0].error or "")
    assert store.get("pipeline.chunk:run-fence:A")["status"] != "SUCCESS"
    store.close()
