"""Evidence-first Brain notification routing."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .email_gateway import AgentMailGateway, EmailGatewayError

SEVERITIES = {"INFO", "WARNING", "ERROR", "CRITICAL"}
DEFAULT_NOTIFY_SEVERITIES = {"ERROR", "CRITICAL"}


@dataclass(frozen=True)
class NotificationDecision:
    event_id: str
    severity: str
    should_notify: bool
    reason: str


@dataclass(frozen=True)
class NotificationEvidence:
    event_id: str
    status: str
    severity: str
    channel: str
    created_at: str
    message_id: str | None = None
    thread_id: str | None = None
    error: str | None = None


class NotificationRouter:
    def __init__(self, *, gateway=None, evidence_path=None, recipient=None, notify_severities=None):
        self.gateway = gateway or AgentMailGateway()
        self.evidence_path = Path(evidence_path or os.getenv("BRAIN_NOTIFICATION_EVIDENCE", ".brain_state/notifications.jsonl"))
        self.recipient = recipient or os.getenv("BRAIN_ALERT_TO")
        self.notify_severities = notify_severities or DEFAULT_NOTIFY_SEVERITIES

    @staticmethod
    def event_id(event_type: str, source: str, fingerprint: str = "") -> str:
        raw = "|".join((event_type.strip(), source.strip(), fingerprint.strip()))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def decide(self, *, event_type: str, source: str, severity: str, fingerprint: str = ""):
        severity = severity.upper().strip()
        if severity not in SEVERITIES:
            raise ValueError(f"unsupported severity: {severity}")
        event_id = self.event_id(event_type, source, fingerprint)
        if severity not in self.notify_severities:
            return NotificationDecision(event_id, severity, False, "severity_not_notifiable")
        if self._already_sent(event_id):
            return NotificationDecision(event_id, severity, False, "duplicate_event")
        if not self.recipient:
            return NotificationDecision(event_id, severity, False, "recipient_not_configured")
        return NotificationDecision(event_id, severity, True, "eligible")

    def notify(self, *, event_type: str, source: str, severity: str, subject: str, text: str, fingerprint: str = ""):
        decision = self.decide(event_type=event_type, source=source, severity=severity, fingerprint=fingerprint)
        now = datetime.now(timezone.utc).isoformat()
        if not decision.should_notify:
            evidence = NotificationEvidence(decision.event_id, "NOT_SENT", decision.severity, "email", now, error=decision.reason)
            self._append(evidence)
            return evidence
        try:
            result = self.gateway.send(to=[self.recipient], subject=subject, text=text)
        except (EmailGatewayError, OSError) as exc:
            evidence = NotificationEvidence(decision.event_id, "SEND_FAILED", decision.severity, "email", now, error=str(exc)[:500])
            self._append(evidence)
            return evidence
        evidence = NotificationEvidence(decision.event_id, "SENT_VERIFIED", decision.severity, "email", now, result.message_id, result.thread_id)
        self._append(evidence)
        return evidence

    def _already_sent(self, event_id: str) -> bool:
        if not self.evidence_path.exists():
            return False
        for line in self.evidence_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("event_id") == event_id and item.get("status") == "SENT_VERIFIED":
                return True
        return False

    def _append(self, evidence: NotificationEvidence) -> None:
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        with self.evidence_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(evidence), sort_keys=True) + "\n")
