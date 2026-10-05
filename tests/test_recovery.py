from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.recovery import RecoveryRunner
from platform_foundation.task_state import TaskStatus


def test_transient_failure_retries_and_succeeds() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        runner = RecoveryRunner(state, audit)
        calls = {"count": 0}

        def handler() -> str:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary")
            return "ok"

        result = runner.run("job-1", handler, max_attempts=3)

        assert result.status is TaskStatus.SUCCESS
        assert result.attempts == 2
        assert result.output == "ok"
        assert state.get("recovery:job-1")["status"] == "SUCCESS"
        assert audit.verify()
        state.close()


def test_max_attempts_ends_failed() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        runner = RecoveryRunner(state, audit)

        def handler() -> None:
            raise ValueError("permanent")

        result = runner.run("job-2", handler, max_attempts=2)

        assert result.status is TaskStatus.FAILED
        assert result.attempts == 2
        assert "permanent" in (result.error or "")
        assert state.get("recovery:job-2")["status"] == "FAILED"
        assert audit.verify()
        state.close()


def test_non_retryable_failure_stops_immediately() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        runner = RecoveryRunner(state, audit)
        calls = {"count": 0}

        def handler() -> None:
            calls["count"] += 1
            raise ValueError("do not retry")

        result = runner.run(
            "job-3",
            handler,
            max_attempts=5,
            retryable=lambda exc: not isinstance(exc, ValueError),
        )

        assert result.status is TaskStatus.FAILED
        assert result.attempts == 1
        assert calls["count"] == 1
        state.close()


def test_checkpoint_survives_restart() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        runner = RecoveryRunner(state, audit)

        calls = {"count": 0}

        def handler() -> str:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("transient")
            return "resumed"

        first = runner.run("job-4", handler, max_attempts=1)
        assert first.status is TaskStatus.FAILED
        assert first.attempts == 1
        state.close()

        reopened = SQLiteStateStore(tmp.name)
        resumed = RecoveryRunner(reopened, audit)
        second = resumed.run("job-4", handler, max_attempts=3)

        assert second.status is TaskStatus.SUCCESS
        assert second.attempts == 2
        assert reopened.get("recovery:job-4")["status"] == "SUCCESS"
        assert audit.verify()
        reopened.close()
