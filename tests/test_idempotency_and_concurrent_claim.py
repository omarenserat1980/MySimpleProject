from __future__ import annotations

import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from brain_v12.brain.durable_task_store import DurableTaskStore


def test_idempotency_returns_same_durable_task():
    with tempfile.TemporaryDirectory() as d:
        store = DurableTaskStore(Path(d) / "tasks.db")
        first = store.submit("request-a", {"value": 1}, "idem-42")
        second = store.submit("request-b", {"value": 2}, "idem-42")

        assert first["task_id"] == "request-a"
        assert second["task_id"] == "request-a"
        assert second["payload"] == first["payload"]
        assert store.counts()["QUEUED"] == 1
        store.close()


def test_concurrent_claim_has_single_winner():
    with tempfile.TemporaryDirectory() as d:
        store = DurableTaskStore(Path(d) / "tasks.db")
        store.submit("race", {"work": True})

        def claim(executor):
            return store.claim("race", executor, lease_seconds=30)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(claim, [f"executor-{i}" for i in range(8)]))

        winners = [r for r in results if r is not None]
        assert len(winners) == 1
        assert winners[0]["status"] == "RUNNING"
        assert winners[0]["attempt"] == 1
        store.close()
