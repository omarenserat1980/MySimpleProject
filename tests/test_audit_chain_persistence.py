from __future__ import annotations

import tempfile
from pathlib import Path

from platform_foundation.audit_chain import AuditChain


def test_audit_chain_survives_restart_and_remains_verifiable():
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "audit.db"

        first = AuditChain(str(path))
        first.record("stage.started", {"stage": 21})
        second = first.record("stage.checkpointed", {"resume": True})
        assert first.verify()
        first.close()

        restarted = AuditChain(str(path))
        events = restarted.events()
        assert restarted.verify()
        assert len(events) == 2
        assert events[-1].event_hash == second.event_hash
        assert events[-1].previous_hash == events[-2].event_hash

        third = restarted.record("stage.resumed", {"stage": 22})
        assert restarted.verify()
        assert third.sequence == 3
        assert third.previous_hash == second.event_hash
        restarted.close()
