from __future__ import annotations

import tempfile
import time
from pathlib import Path

from brain_v12.brain.durable_task_store import DurableTaskStore


def test_expired_executor_cannot_commit_after_recovery():
    with tempfile.TemporaryDirectory() as d:
        store = DurableTaskStore(Path(d) / "tasks.db")
        store.submit("fenced", {"work": "x"})

        first = store.claim("fenced", "executor-old", lease_seconds=1)
        assert first is not None
        old_lease = first["lease_id"]

        time.sleep(1.1)
        assert store.recover_expired() == ["fenced"]

        second = store.claim("fenced", "executor-new", lease_seconds=30)
        assert second is not None
        new_lease = second["lease_id"]
        assert new_lease != old_lease

        stale_commit = store.finish("fenced", old_lease, True, {"owner": "old"})
        assert stale_commit is None
        assert store.get("fenced")["status"] == "RUNNING"

        valid_commit = store.finish("fenced", new_lease, True, {"owner": "new"})
        assert valid_commit is not None
        assert valid_commit["status"] == "COMPLETED"
        assert valid_commit["result_json"] == '{"owner": "new"}'
        store.close()
