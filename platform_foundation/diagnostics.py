from __future__ import annotations

from dataclasses import asdict, dataclass
import traceback
from typing import Any


@dataclass(frozen=True)
class DiagnosticEvidence:
    task_id: str
    error_type: str
    error: str
    traceback: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def capture_exception(task_id: str, exc: BaseException) -> DiagnosticEvidence:
    return DiagnosticEvidence(
        task_id=task_id,
        error_type=type(exc).__name__,
        error=str(exc),
        traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )


__all__ = ["DiagnosticEvidence", "capture_exception"]
