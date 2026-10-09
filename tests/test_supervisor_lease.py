import tempfile
import threading
import time

from platform_foundation.audit_chain import AuditChain
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.supervisor import Supervisor
from platform_foundation.task_state import TaskStatus


def test_supervisor_lease_prevents_duplicate_execution():
    with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
        state = SQLiteStateStore(tmp.name)
        audit = AuditChain()
        permissions = PermissionBoundary({'build': ActionRisk.WRITE})
        first = Supervisor(state, audit, permissions)
        second = Supervisor(state, audit, permissions)
        entered = threading.Event()
        release = threading.Event()
        calls = {'count': 0}

        def handler():
            calls['count'] += 1
            entered.set()
            release.wait(timeout=5)
            return 'single-artifact'

        first.register('job-lease', 'build', ActionRisk.WRITE, handler)
        second.register('job-lease', 'build', ActionRisk.WRITE, lambda: 'duplicate')
        results = []
        thread = threading.Thread(target=lambda: results.append(first.run('job-lease')))
        thread.start()
        assert entered.wait(timeout=5)

        duplicate = second.run('job-lease')
        assert duplicate.status is TaskStatus.FAILED
        assert duplicate.error == 'task lease unavailable'

        release.set()
        thread.join(timeout=5)
        assert len(results) == 1
        assert results[0].status is TaskStatus.SUCCESS
        assert calls['count'] == 1
        assert audit.verify()
        state.close()