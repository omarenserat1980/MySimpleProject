from __future__ import annotations

import tempfile

from platform_foundation.durable_audit import SQLiteAuditChain


def test_durable_audit_survives_restart_and_preserves_chain() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        first = SQLiteAuditChain(tmp.name)
        first.record("process.started", {"pid": "first"})
        first.record("checkpoint.saved", {"step": 4})
        assert first.verify()
        first.close()

        second = SQLiteAuditChain(tmp.name)
        second.record("process.resumed", {"pid": "second"})
        assert second.verify()
        events = second.events()
        assert [event.sequence for event in events] == [1, 2, 3]
        assert events[2].previous_hash == events[1].event_hash
        second.close()


def test_durable_audit_detects_database_tampering() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        audit = SQLiteAuditChain(tmp.name)
        audit.record("artifact.created", {"name": "a"})
        audit.close()

        import sqlite3

        conn = sqlite3.connect(tmp.name)
        conn.execute("UPDATE audit_events SET payload=? WHERE sequence=1", ('{"name":"tampered"}',))
        conn.commit()
        conn.close()

        reopened = SQLiteAuditChain(tmp.name)
        assert reopened.verify() is False
        reopened.close()
