"""Evidence-first customer communications core.

This module is intentionally transport-neutral. Email, portal, chat and future
messaging providers are adapters; the hub owns lifecycle, provenance and
idempotency.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
import tempfile
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    message_id: str = field(default_factory=lambda: "MSG-" + uuid.uuid4().hex)
    state: MessageState = MessageState.DRAFTED
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    content_hash: str = ""
    transport_evidence_ref: str | None = None
    events: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.direction not in {"INBOUND", "OUTBOUND"}:
            raise ValueError("direction must be INBOUND or OUTBOUND")
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.body.encode("utf-8")).hexdigest()
        self._event("CREATED")

    def _event(self, event: str, **extra) -> None:
        self.events.append({"event": event, "at": _now(), **extra})
        self.updated_at = _now()

    def transition(self, new_state: MessageState, evidence_ref: str | None = None) -> None:
        if new_state not in _ALLOWED[self.state]:
            raise ValueError(f"invalid transition {self.state} -> {new_state}")
        if new_state in {MessageState.SENT, MessageState.DELIVERED} and not evidence_ref:
            raise ValueError("transport evidence is required for SENT/DELIVERED")
        self.state = new_state
        if evidence_ref:
            self.transport_evidence_ref = evidence_ref
        self._event("STATE_CHANGED", state=new_state.value, evidence_ref=evidence_ref)


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
            with open(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.flush()
            Path(tmp).replace(path)
        finally:
            Path(tmp).unlink(missing_ok=True)

    def _index(self) -> dict:
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save(self, message: CommunicationMessage) -> None:
        self._atomic_write(
            self.messages_dir / f"{message.message_id}.json",
            asdict(message),
        )
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
        data = json.loads(
            (self.messages_dir / f"{message_id}.json").read_text(encoding="utf-8")
        )
        data["channel"] = Channel(data["channel"])
        data["state"] = MessageState(data["state"])
        return CommunicationMessage(**{
            k: v for k, v in data.items()
            if k not in {"events", "content_hash", "created_at", "updated_at", "message_id", "state"}
        }, message_id=data["message_id"], state=data["state"],
           created_at=data["created_at"], updated_at=data["updated_at"],
           content_hash=data["content_hash"], events=data["events"],
           transport_evidence_ref=data["transport_evidence_ref"])

    def transition(self, message_id: str, new_state: MessageState, evidence_ref: str | None = None) -> CommunicationMessage:
        message = self.get(message_id)
        message.transition(new_state, evidence_ref=evidence_ref)
        self._save(message)
        return message

    def list_customer(self, customer_id: str) -> list[CommunicationMessage]:
        result = []
        for path in sorted(self.messages_dir.glob("MSG-*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("customer_id") == customer_id:
                result.append(self.get(data["message_id"]))
        return result
