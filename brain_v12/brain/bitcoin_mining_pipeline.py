"""Sequential Bitcoin mining pipeline.

The pipeline turns each verified stage into the prerequisite for the next.
It never grants external-resource authorization implicitly and never treats
simulation or projected income as revenue.
"""

from __future__ import annotations

from dataclasses import dataclass, field


STAGES = (
    "SOFTWARE_READY",
    "WORKER_AUTHORIZED",
    "SHA256D_EXECUTION",
    "POOL_CONFIGURED",
    "STRATUM_CONNECTED",
    "SHARES_ACCEPTED",
    "PAYOUT_OBSERVED",
    "BTC_RECEIVED",
    "REVENUE_REALIZED",
)


@dataclass
class PipelineState:
    completed: list[str] = field(default_factory=list)
    blocked_reason: str | None = None

    def advance(self, stage: str) -> None:
        if stage not in STAGES:
            raise ValueError("unknown_stage")
        index = STAGES.index(stage)
        if index > len(self.completed):
            raise RuntimeError("prerequisite_stage_missing")
        if index == len(self.completed):
            self.completed.append(stage)

    def next_stage(self) -> str | None:
        if len(self.completed) >= len(STAGES):
            return None
        return STAGES[len(self.completed)]

    def snapshot(self) -> dict:
        return {
            "completed": list(self.completed),
            "next_stage": self.next_stage(),
            "blocked_reason": self.blocked_reason,
            "revenue_realized": "REVENUE_REALIZED" in self.completed,
        }


def prerequisite_for(stage: str) -> str | None:
    if stage not in STAGES:
        raise ValueError("unknown_stage")
    index = STAGES.index(stage)
    return STAGES[index - 1] if index else None
