"""Auditable decision records for the YouTube factory."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    video_id: str
    stage: str
    action: str
    reason: str
    evidence_refs: tuple[str, ...] = ()

    def fingerprint(self) -> str:
        payload = json.dumps(
            {
                "decision_id": self.decision_id,
                "video_id": self.video_id,
                "stage": self.stage,
                "action": self.action,
                "reason": self.reason,
                "evidence_refs": self.evidence_refs,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def unique_decisions(records: list[DecisionRecord]) -> list[DecisionRecord]:
    seen: set[str] = set()
    result: list[DecisionRecord] = []
    for record in records:
        if record.decision_id in seen:
            continue
        seen.add(record.decision_id)
        result.append(record)
    return result
