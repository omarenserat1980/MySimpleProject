"""Company-level executive facade over Brain's existing subsystems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .brain_executive import BrainExecutive, CompanyObjective, ExecutiveDecision


@dataclass
class ExecutiveSubsystems:
    supervisor: Any | None = None
    memory: Any | None = None
    economic: Any | None = None
    opportunity: Any | None = None
    product: Any | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class CompanyExecutive:
    """Single operational decision authority for Brain-owned company work.

    Subsystems remain specialists; this facade decides what should be worked
    on next and delegates execution. It does not bypass external-authority
    gates already enforced by the underlying subsystem.
    """

    def __init__(self, *, executive: BrainExecutive | None = None,
                 subsystems: ExecutiveSubsystems | None = None):
        self.executive = executive or BrainExecutive()
        self.subsystems = subsystems or ExecutiveSubsystems()

    def discover_objectives(self, objectives: list[CompanyObjective]) -> None:
        self.executive.load_objectives(objectives)

    def decide(self) -> ExecutiveDecision:
        return self.executive.decide()

    def cycle(self, executor: Callable[[ExecutiveDecision], bool] | None = None) -> dict[str, Any]:
        decision = self.decide()
        if decision.status == "READY":
            verified = True if executor is None else bool(executor(decision))
            if verified:
                self.executive.complete(decision.objective_id)
                result = "COMPLETED"
            else:
                result = "EXECUTION_FAILED"
        elif decision.status == "GATED":
            self.executive.block(decision.objective_id)
            result = "GATED"
        else:
            self.executive.state.cycle += 1
            result = "DISCOVERY_REQUIRED"
        return {
            "mode": self.executive.state.mode,
            "cycle": self.executive.state.cycle,
            "result": result,
            "decision": decision,
            "subsystems": [k for k,v in self.subsystems.__dict__.items()
                           if k != "extras" and v is not None],
        }
