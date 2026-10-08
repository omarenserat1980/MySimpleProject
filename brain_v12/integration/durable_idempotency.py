"""Durable idempotency gate backed by Brain EvidenceStore."""
from .idempotency_gate import ExecutionIntent
from ..brain.evidence_store import EvidenceStore

class DurableIdempotencyGate:
    def __init__(self,evidence_store:EvidenceStore):
        self.store=evidence_store

    def claim(self,intent:ExecutionIntent):
        return self.store.claim_execution(
            intent.execution_key,
            intent.mission_fingerprint,
            intent.action,
            intent.parameters_fingerprint,
        )

    def complete(self,intent:ExecutionIntent):
        return self.store.complete_execution(intent.execution_key)

    def status(self,intent:ExecutionIntent):
        return self.store.execution_status(intent.execution_key)
