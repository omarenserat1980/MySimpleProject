"""Versioned self-improvement proposals with validation gates and rollback."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

@dataclass
class ImprovementProposal:
    id: str
    description: str
    status: str = "PROPOSED"
    created_at: str = ""

class SelfImprovementEngine:
    def __init__(self):
        self.proposals: dict[str, ImprovementProposal] = {}
        self.validators: dict[str, Callable[[], bool]] = {}
        self.snapshots: list[str] = []

    def propose(self, proposal_id: str, description: str):
        p = ImprovementProposal(
            id=proposal_id,
            description=description,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.proposals[proposal_id] = p
        return p

    def register_validator(self, proposal_id: str, validator: Callable[[], bool]):
        self.validators[proposal_id] = validator

    def validate(self, proposal_id: str):
        p = self.proposals[proposal_id]
        validator = self.validators.get(proposal_id)
        if validator is None:
            p.status = "NEEDS_VALIDATOR"
            return False
        try:
            ok = bool(validator())
        except Exception:
            ok = False
        p.status = "VALIDATED" if ok else "REJECTED"
        return ok

    def mark_applied(self, proposal_id: str, snapshot_id: str):
        p = self.proposals[proposal_id]
        if p.status != "VALIDATED":
            raise RuntimeError("proposal must be validated before applying")
        self.snapshots.append(snapshot_id)
        p.status = "APPLIED"

    def rollback_target(self):
        return self.snapshots[-1] if self.snapshots else None

    def status(self):
        return {
            "proposals": len(self.proposals),
            "applied": sum(p.status == "APPLIED" for p in self.proposals.values()),
            "last_snapshot": self.rollback_target(),
        }
