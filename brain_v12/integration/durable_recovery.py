"""Durable recovery lease for interrupted executions."""
from ..brain.evidence_store import EvidenceStore
from .idempotency_gate import ExecutionIntent

class ExecutionRecovery:
    def __init__(self,store:EvidenceStore):
        self.store=store

    def renew(self,intent:ExecutionIntent,lease_seconds=300):
        return self.store.renew_execution(intent.execution_key,lease_seconds)

    def stale(self):
        return self.store.recoverable_executions()

    def status(self,intent:ExecutionIntent):
        return self.store.execution_status(intent.execution_key)
