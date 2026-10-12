from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from time import time
from typing import Any


class FailureKind(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERMISSION = "PERMISSION"
    INPUT = "INPUT"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class FailureRecord:
    sequence: int
    timestamp: float
    job_id: str
    kind: str
    error_type: str
    retryable: bool


class FailureTracker:
    """Classifies failures conservatively; it records retryability but never retries."""

    def __init__(self) -> None:
        self._records: list[FailureRecord] = []

    @staticmethod
    def classify(exc: BaseException) -> tuple[FailureKind, bool]:
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return FailureKind.TRANSIENT, True
        if isinstance(exc, PermissionError):
            return FailureKind.PERMISSION, False
        if isinstance(exc, (ValueError, TypeError)):
            return FailureKind.INPUT, False
        return FailureKind.INTERNAL, False

    def record(self, job_id: str, exc: BaseException) -> FailureRecord:
        kind, retryable = self.classify(exc)
        record = FailureRecord(
            sequence=len(self._records) + 1,
            timestamp=time(),
            job_id=job_id,
            kind=kind.value,
            error_type=type(exc).__name__,
            retryable=retryable,
        )
        self._records.append(record)
        return record

    def records(self) -> list[dict[str, Any]]:
        return [asdict(record) for record in self._records]

    def is_ready(self) -> bool:
        return isinstance(self._records, list)
