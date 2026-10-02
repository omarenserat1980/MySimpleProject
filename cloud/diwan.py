"""Durable core primitives for BRAIN Dيوان & Secretariat.

This module intentionally keeps the first implementation storage-simple and
dependency-light. It provides stable identifiers, lifecycle validation,
case-file linking, document versioning metadata, routing and retention state.
The API layer can persist these records using the same Brain state backend.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Optional
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CorrespondenceState(str, Enum):
    RECEIVED = "RECEIVED"
    REGISTERED = "REGISTERED"
    CLASSIFIED = "CLASSIFIED"
    LINKED = "LINKED"
    ROUTED = "ROUTED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    RESPONDED = "RESPONDED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    CANCELLED = "CANCELLED"
    LEGAL_HOLD = "LEGAL_HOLD"


class RecordState(str, Enum):
    CAPTURED = "CAPTURED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    RETENTION = "RETENTION"
    REVIEW = "REVIEW"
    ARCHIVED = "ARCHIVED"


@dataclass
class Correspondence:
    direction: str
    subject: str
    channel: str
    sender: Optional[str] = None
    recipients: list[str] = field(default_factory=list)
    case_id: Optional[str] = None
    classification: str = "UNCLASSIFIED"
    confidentiality: str = "INTERNAL"
    content_ref: Optional[str] = None
    attachments: list[str] = field(default_factory=list)
    correspondence_id: str = field(default_factory=lambda: str(uuid4()))
    number: Optional[str] = None
    state: CorrespondenceState = CorrespondenceState.RECEIVED
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    events: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, new_state: CorrespondenceState, actor: str, reason: str = "") -> None:
        allowed = {
            CorrespondenceState.RECEIVED: {CorrespondenceState.REGISTERED, CorrespondenceState.REJECTED, CorrespondenceState.DUPLICATE},
            CorrespondenceState.REGISTERED: {CorrespondenceState.CLASSIFIED, CorrespondenceState.REJECTED, CorrespondenceState.DUPLICATE},
            CorrespondenceState.CLASSIFIED: {CorrespondenceState.LINKED, CorrespondenceState.ROUTED},
            CorrespondenceState.LINKED: {CorrespondenceState.ROUTED},
            CorrespondenceState.ROUTED: {CorrespondenceState.IN_PROGRESS, CorrespondenceState.WAITING, CorrespondenceState.CANCELLED},
            CorrespondenceState.IN_PROGRESS: {CorrespondenceState.WAITING, CorrespondenceState.RESPONDED, CorrespondenceState.CLOSED},
            CorrespondenceState.WAITING: {CorrespondenceState.IN_PROGRESS, CorrespondenceState.RESPONDED, CorrespondenceState.CANCELLED},
            CorrespondenceState.RESPONDED: {CorrespondenceState.CLOSED, CorrespondenceState.WAITING},
            CorrespondenceState.CLOSED: {CorrespondenceState.ARCHIVED, CorrespondenceState.LEGAL_HOLD},
            CorrespondenceState.ARCHIVED: {CorrespondenceState.LEGAL_HOLD},
            CorrespondenceState.LEGAL_HOLD: {CorrespondenceState.CLOSED, CorrespondenceState.ARCHIVED},
        }
        if new_state not in allowed.get(self.state, set()):
            raise ValueError(f"invalid correspondence transition: {self.state} -> {new_state}")
        self.state = new_state
        self.updated_at = now_iso()
        self.events.append({"at": self.updated_at, "actor": actor, "state": new_state.value, "reason": reason})


@dataclass
class CaseFile:
    title: str
    owner_type: str
    owner_id: str
    case_id: str = field(default_factory=lambda: str(uuid4()))
    number: Optional[str] = None
    state: str = "OPEN"
    opened_at: str = field(default_factory=now_iso)
    closed_at: Optional[str] = None
    correspondence_ids: list[str] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)
    approval_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)


@dataclass
class DocumentVersion:
    document_id: str
    version: int
    filename: str
    content_ref: str
    content_sha256: str
    created_at: str = field(default_factory=now_iso)
    created_by: str = "system"
    supersedes: Optional[int] = None


@dataclass
class RoutingAssignment:
    record_id: str
    target: str
    assigned_by: str
    assigned_at: str = field(default_factory=now_iso)
    deadline_at: Optional[str] = None
    status: str = "ASSIGNED"
    notes: str = ""


def content_hash(content: bytes) -> str:
    return sha256(content).hexdigest()


def register_number(prefix: str, sequence: int, year: Optional[int] = None) -> str:
    y = year or datetime.now(timezone.utc).year
    return f"{prefix}-{y}-{sequence:06d}"


def archive_eligible(record_state: RecordState, legal_hold: bool = False) -> bool:
    return record_state in {RecordState.CLOSED, RecordState.REVIEW, RecordState.ARCHIVED} and not legal_hold


def to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
