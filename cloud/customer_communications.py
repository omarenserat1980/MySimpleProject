"""Evidence-first customer communications core.

The hub is transport-neutral: adapters deliver messages, while this module owns
identity, lifecycle, idempotency, retry metadata, SLA/escalation state and
durable provenance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


class Channel(str, Enum):
    CUSTOMER_PORTAL = "CUSTOMER_PORTAL"
    EMAIL = "EMAIL"
    WEB_CHAT = "WEB_CHAT"
    API = "API"
    MESSAGING_ADAPTER = "MESSAGING_ADAPTER"


class MessageState(str, Enum):
    DRAFTED = "DRAFTED"
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BOUNCED = "BOUNCED"
    LEGAL_HOLD = "LEGAL_HOLD"


class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


_ALLOWED = {
    MessageState.DRAFTED: {MessageState.QUEUED, MessageState.CANCELLED},
    MessageState.QUEUED: {MessageState.SENT, MessageState.FAILED, MessageState.CANCELLED},
    MessageState.SENT: {MessageState.DELIVERED, MessageState.BOUNCED, MessageState.FAILED},
    MessageState.DELIVERED: {MessageState.ACKNOWLEDGED, MessageState.CLOSED, MessageState.LEGAL_HOLD},
    MessageState.ACKNOWLEDGED: {MessageState.CLOSED, MessageState.LEGAL_HOLD},
    MessageState.CLOSED: {MessageState.LEGAL_HOLD},
    MessageState.FAILED: {MessageState.QUEUED, MessageState.CANCELLED},
    MessageState.CANCELLED: set(),
    MessageState.BOUNCED: {MessageState.QUEUED, MessageState.CANCELLED},
    MessageState.LEGAL_HOLD: set(),
}


@dataclass
class CommunicationMessage:
    customer_id: str
    channel: Channel
    direction: str
    body: str
    thread_id: str | None = None
    case_id: str | None = None
    request_id: str | None = None
    consent_scope: str | None = None
    idempotency_key: str | None = None
    priority: Priority = Priority.NORMAL
    sla_minutes: int = 1440
    message_id: str = field(default_factory=lambda: "MSG-" + uuid.uuid4().hex)
    state: MessageState = MessageState.DRAFTED
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    content_hash: str = ""
    transport_evidence_ref: str | None = None
    attempt: int = 0
    last_error: str | None = None
    assigned_to: str | None = None
    escalation_state: str = "NONE"
    events: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.direction not in {"INBOUND", "OUTBOUND"}:
            raise ValueError("direction must be INBOUND or OUTBOUND")
        if self.sla_minutes <= 0:
            raise ValueError("sla_minutes must be positive")
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.body.encode("utf-8")).hexdigest()
        if not self.events:
            self._event("CREATED")

    @classmethod
    def from_dict(cls, data: dict) -> "CommunicationMessage":
        payload = dict(data)
        payload["channel"] = Channel(payload["channel"])
        payload["state"] = MessageState(payload["state"])
        payload["priority"] = Priority(payload.get("priority", Priority.NORMAL))
        return cls(**payload)

    def _event(self, event: str, **extra) -> None:
        self.events.append({"event": event, "at": _now(), **extra})
        self.updated_at = _now()

    @property
    def sla_due_at(self) -> str:
        return (_parse(self.created_at) + timedelta(minutes=self.sla_minutes)).isoformat()

    def sla_overdue(self, now: datetime | None = None) -> bool:
        if self.state in {MessageState.CLOSED, MessageState.CANCELLED, MessageState.LEGAL_HOLD}:
            return False
        return (now or datetime.now(timezone.utc)) > _parse(self.sla_due_at)

    def transition(self, new_state: MessageState, evidence_ref: str | None = None, error: str | None = None) -> None:
        if new_state not in _ALLOWED[self.state]:
            raise ValueError(f"invalid transition {self.state} -> {new_state}")
        if new_state in {MessageState.SENT, MessageState.DELIVERED} and not evidence_ref:
            raise ValueError("transport evidence is required for SENT/DELIVERED")
        if new_state in {MessageState.SENT, MessageState.QUEUED}:
            self.attempt += 1 if new_state == MessageState.SENT else 0
        self.state = new_state
        self.last_error = error
        if evidence_ref:
            self.transport_evidence_ref = evidence_ref
        self._event("STATE_CHANGED", state=new_state.value, evidence_ref=evidence_ref, error=error)
        if self.sla_overdue():
            self.escalation_state = "OVERDUE"
            self._event("SLA_OVERDUE", due_at=self.sla_due_at)

    def assign(self, actor: str) -> None:
        if not actor.strip():
            raise ValueError("actor is required")
        self.assigned_to = actor
        self._event("ASSIGNED", actor=actor)

    def escalate(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("escalation reason is required")
        self.escalation_state = "ESCALATED"
        self._event("ESCALATED", reason=reason)


class CommunicationHub:
    def __init__(self, root: str | Path = ".brain_state/customer_communications"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.messages_dir = self.root / "messages"
        self.messages_dir.mkdir(exist_ok=True)
        self.index_path = self.root / "idempotency.json"
        if not self.index_path.exists():
            self._atomic_write(self.index_path, {})

    def _atomic_write(self, path: Path, payload) -> None:
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            Path(tmp).replace(path)
        finally:
            Path(tmp).unlink(missing_ok=True)

    def _index(self) -> dict:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save(self, message: CommunicationMessage) -> None:
        self._atomic_write(self.messages_dir / f"{message.message_id}.json", asdict(message))
        if message.idempotency_key:
            idx = self._index()
            idx[message.idempotency_key] = message.message_id
            self._atomic_write(self.index_path, idx)

    def create(self, **kwargs) -> CommunicationMessage:
        key = kwargs.get("idempotency_key")
        if key:
            existing = self._index().get(key)
            if existing:
                return self.get(existing)
        message = CommunicationMessage(**kwargs)
        self._save(message)
        return message

    def get(self, message_id: str) -> CommunicationMessage:
        path = self.messages_dir / f"{message_id}.json"
        if not path.exists():
            raise FileNotFoundError(message_id)
        return CommunicationMessage.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def transition(self, message_id: str, new_state: MessageState,
                   evidence_ref: str | None = None, error: str | None = None) -> CommunicationMessage:
        message = self.get(message_id)
        message.transition(new_state, evidence_ref=evidence_ref, error=error)
        self._save(message)
        return message

    def assign(self, message_id: str, actor: str) -> CommunicationMessage:
        message = self.get(message_id)
        message.assign(actor)
        self._save(message)
        return message

    def escalate(self, message_id: str, reason: str) -> CommunicationMessage:
        message = self.get(message_id)
        message.escalate(reason)
        self._save(message)
        return message

    def list_customer(self, customer_id: str) -> list[CommunicationMessage]:
        result = []
        for path in sorted(self.messages_dir.glob("MSG-*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("customer_id") == customer_id:
                result.append(self.get(data["message_id"]))
        return result

    def list_overdue(self) -> list[CommunicationMessage]:
        return [m for path in sorted(self.messages_dir.glob("MSG-*.json"))
                if (m := self.get(path.stem)).sla_overdue()]
