from __future__ import annotations

import threading
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.parallel_chunks import ParallelChunkRunner
from platform_foundation.persistent_state import SQLiteStateStore


def test_chunks_run_with_bounded_parallelism(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)
    active = {"value": 0, "max": 0}
    lock = threading.Lock()

    def execute(chunk):
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
    assert all(store.get(f"pipeline.chunk:run-1:{i}")["status"] == "SUCCESS" for i in ["1","2","3","4"])
    assert audit.verify()
    store.close()


def test_restart_resumes_only_unfinished_chunks(tmp_path):
    path = tmp_path / "state.db"
    store = SQLiteStateStore(path)
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)
    calls = []

    def first(chunk):
        calls.append(chunk)
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

    def second(chunk):
        resumed_calls.append(chunk)
        return chunk

    second_results = resumed.run(
        "run-2", ["1", "2", "3"], second,
        lambda _chunk, output: True,
        max_workers=2,
    )

    assert [r.status for r in second_results] == ["SUCCESS", "SUCCESS", "SUCCESS"]
    assert resumed_calls == ["3"]
    assert audit.verify()
    reopened.close()


def test_failed_chunk_never_becomes_success_without_verification(tmp_path):
    store = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    runner = ParallelChunkRunner(store, audit)

    results = runner.run(
        "run-3", ["bad"], lambda _chunk: "output",
        lambda _chunk, _output: False,
        max_workers=1,
    )

    assert results[0].status == "FAILED"
    assert store.get("pipeline.chunk:run-3:bad")["status"] == "FAILED"
    assert audit.verify()
    store.close()
