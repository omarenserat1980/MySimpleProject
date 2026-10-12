"""Evidence-based commercial incident recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from .audit import ProviderAuditLog, ProviderEvent
from .containment import CommercialContainmentGate


@dataclass(frozen=True)
class RecoveryResult:
    incident_id: str
    recovered: bool
    reason: str


class CommercialRecoveryGate:
    def __init__(self, containment: CommercialContainmentGate, audit: ProviderAuditLog) -> None:
        self.containment = containment
        self.audit = audit

    def recover(
        self,
        incident_id: str,
        order_id: str,
        verifier: Callable[[], bool],
    ) -> RecoveryResult:
        incidents = [
            i for i in self.containment.active_incidents(order_id)
            if i.incident_id == incident_id
        ]
        if not incidents:
            return RecoveryResult(incident_id, False, "ACTIVE_INCIDENT_NOT_FOUND")

        try:
            verified = bool(verifier())
        except Exception:
            verified = False

        if not verified:
            self.audit.append(ProviderEvent.create(
                f"recovery-{incident_id}",
                order_id,
                "RECOVERY_BLOCKED",
                "incident condition not cleared",
            ))
            return RecoveryResult(incident_id, False, "RECOVERY_VERIFICATION_FAILED")

        self.containment.release(incident_id)
        self.audit.append(ProviderEvent.create(
            f"recovered-{incident_id}",
            order_id,
            "RECOVERY_VERIFIED",
            "incident condition cleared by independent verification",
            metadata={"recovered_at": datetime.now(timezone.utc).isoformat()},
        ))
        return RecoveryResult(incident_id, True, "RECOVERY_VERIFIED")
