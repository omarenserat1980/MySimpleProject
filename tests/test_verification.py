from __future__ import annotations

import tempfile

from platform_foundation.audit_chain import AuditChain
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.task_state import TaskStatus
from platform_foundation.verification import VerificationGate


def test_verification_requires_positive_evidence() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        gate = VerificationGate(state, audit)

        result = gate.verify("job-1", {"artifact": "ok"}, lambda value: value["artifact"] == "ok")

        assert result.status is TaskStatus.SUCCESS
        assert result.verified is True
        assert state.get("verification:job-1")["verified"] is True
        assert audit.verify()
        state.close()


def test_false_verification_is_failure() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        gate = VerificationGate(state, audit)

        result = gate.verify("job-2", {"artifact": "missing"}, lambda value: value["artifact"] == "ok")

        assert result.status is TaskStatus.FAILED
        assert result.verified is False
        assert "predicate" in (result.error or "")
        assert state.get("verification:job-2")["status"] == "FAILED"
        state.close()


def test_verifier_exception_is_failure() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        gate = VerificationGate(state, audit)

        def verifier(_value: object) -> bool:
            raise RuntimeError("qc unavailable")

        result = gate.verify("job-3", "artifact", verifier)

        assert result.status is TaskStatus.FAILED
        assert result.verified is False
        assert "qc unavailable" in (result.error or "")
        assert audit.verify()
        state.close()
