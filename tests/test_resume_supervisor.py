from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.resume_supervisor import ResumeSupervisor
from platform_foundation.task_state import TaskStatus


def test_resume_uses_durable_checkpoint_after_restart() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        supervisor = ResumeSupervisor(state, audit)
        supervisor.checkpoint("job-1", {"step": 7, "input": "kept"})
        state.close()

        reopened = SQLiteStateStore(tmp.name)
        resumed = ResumeSupervisor(reopened, audit)

        result = resumed.run(
            "job-1",
            lambda checkpoint: {"continued_from": checkpoint["step"]},
        )

        assert result.status is TaskStatus.SUCCESS
        assert result.resumed is True
        assert result.checkpoint == {"step": 7, "input": "kept"}
        assert result.output == {"continued_from": 7}
        assert audit.verify()
        reopened.close()


def test_missing_checkpoint_is_a_fresh_start() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        supervisor = ResumeSupervisor(state, audit)

        result = supervisor.run("job-2", lambda checkpoint: checkpoint or "fresh")

        assert result.status is TaskStatus.SUCCESS
        assert result.resumed is False
        assert result.checkpoint is None
        assert result.output == "fresh"
        assert audit.verify()
        state.close()


def test_resume_failure_is_persisted() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        supervisor = ResumeSupervisor(state, audit)
        supervisor.checkpoint("job-3", "checkpoint")

        result = supervisor.run(
            "job-3",
            lambda _checkpoint: (_ for _ in ()).throw(RuntimeError("resume failure")),
        )

        assert result.status is TaskStatus.FAILED
        assert "resume failure" in (result.error or "")
        assert state.get("resume:job-3")["status"] == "FAILED"
        assert audit.verify()
        state.close()
