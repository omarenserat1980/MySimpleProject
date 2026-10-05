from __future__ import annotations

import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.lease import TaskLease
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.supervisor import Supervisor
from platform_foundation.task_state import TaskStatus


def test_supervisor_final_fencing_rejects_replaced_lease(tmp_path):
    state = SQLiteStateStore(tmp_path / "state.db")
    audit = AuditChain()
    supervisor = Supervisor(state, audit, PermissionBoundary({"read": ActionRisk.READ}))

    def handler():
        state.set("lease:final-fence", {"owner": "replacement", "expires_at": time.time() + 30})
        return "output"

    supervisor.register("final-fence", "read", ActionRisk.READ, handler, max_attempts=1)
    result = supervisor.run("final-fence", lease_ttl_seconds=1)

    assert result.status == TaskStatus.FAILED
    assert result.error == "execution lease lost"
    assert any(event.event == "task.lease_lost" for event in audit.events())
    assert audit.verify()
    state.close()