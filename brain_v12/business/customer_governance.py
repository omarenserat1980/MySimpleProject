"""Customer governance layer: evidence, consent, communication and financial gates.

This module is policy/state logic only. It does not send messages, move money,
or execute external actions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from time import time

COMMUNICATION_CHANNELS = ("BRAIN_PORTAL", "EMAIL", "WHATSAPP", "TELEGRAM", "SOCIAL")
CONSENT_PURPOSES = ("SERVICE", "MARKETING", "SUPPORT", "ANALYTICS")
EXTERNAL_ACTIONS = ("SEND_MESSAGE", "PUBLISH", "CONTRACT", "INVOICE", "PAYMENT", "REFUND")

@dataclass
class Consent:
    purpose: str
    granted: bool
    source: str
    recorded_at: float = field(default_factory=time)

    def validate(self) -> None:
        if self.purpose not in CONSENT_PURPOSES:
            raise ValueError("unknown consent purpose")
        if not self.source.strip():
            raise ValueError("consent source required")

@dataclass
class CustomerProfile:
    customer_id: str
    display_name: str
    contact_channels: list[str] = field(default_factory=list)
    consents: list[Consent] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add_consent(self, consent: Consent) -> dict:
        consent.validate()
        self.consents.append(consent)
        return self.snapshot()

    def add_evidence(self, evidence: str) -> dict:
        if not evidence.strip():
            raise ValueError("evidence required")
        self.evidence.append(evidence.strip())
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "display_name": self.display_name,
            "contact_channels": list(self.contact_channels),
            "consents": [c.__dict__.copy() for c in self.consents],
            "evidence": list(self.evidence),
            "notes": list(self.notes),
        }

@dataclass
class CustomerOperation:
    customer_id: str
    action: str
    channel: str | None = None
    purpose: str = "SERVICE"
    evidence: list[str] = field(default_factory=list)

    def authorize(self, profile: CustomerProfile) -> dict:
        if self.action not in EXTERNAL_ACTIONS:
            return {"status": "BLOCKED", "reason": "UNKNOWN_ACTION"}

        if self.action in {"SEND_MESSAGE", "PUBLISH"}:
            if not self.channel or self.channel not in COMMUNICATION_CHANNELS:
                return {"status": "BLOCKED", "reason": "CHANNEL_NOT_APPROVED"}
            if self.purpose not in CONSENT_PURPOSES:
                return {"status": "BLOCKED", "reason": "INVALID_PURPOSE"}
            has_consent = any(c.purpose == self.purpose and c.granted for c in profile.consents)
            if not has_consent:
                return {"status": "REQUIRES_CONSENT", "reason": "NO_VALID_CONSENT"}

        if self.action in {"CONTRACT", "INVOICE", "PAYMENT", "REFUND"} and not self.evidence:
            return {"status": "REQUIRES_AUTHORIZATION", "reason": "EVIDENCE_REQUIRED"}

        return {
            "status": "REQUIRES_AUTHORIZATION",
            "reason": "EXTERNAL_ACTION_GATE",
            "customer_id": profile.customer_id,
            "action": self.action,
            "channel": self.channel,
            "purpose": self.purpose,
        }

def build_customer_policy() -> dict:
    return {
        "external_execution": False,
        "financial_execution": False,
        "data_minimization": True,
        "evidence_required": True,
        "marketing_requires_consent": True,
        "customer_decision_is_human": True,
        "allowed_channels": list(COMMUNICATION_CHANNELS),
        "external_actions": list(EXTERNAL_ACTIONS),
        "policy_state": "GOVERNED",
    }
