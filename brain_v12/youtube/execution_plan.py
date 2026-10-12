"""Safe execution-plan compiler for the YouTube Control Plane.

It produces an ordered plan only. It never executes external actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .control_plane import ControlDecision


class PlanStep(str, Enum):
    DRAFT = "DRAFT"
    RENDER = "RENDER"
    QC = "QC"
    PUBLISH = "PUBLISH"
    MEASURE = "MEASURE"
    LEARN = "LEARN"


@dataclass(frozen=True)
class ExecutionPlan:
    video_id: str
    steps: tuple[PlanStep, ...]
    requires_publish_authorization: bool
    side_effects: bool = False


def compile_execution_plan(decision: ControlDecision) -> ExecutionPlan:
    if decision.duplicate:
        return ExecutionPlan(
            decision.audit.video_id,
            (),
            False,
        )

    action = decision.action
    if action == "DO_NOT_PRODUCE" or action == "FIX_QC":
        return ExecutionPlan(decision.audit.video_id, (), False)
    if action == "PUBLISH_THEN_MEASURE":
        return ExecutionPlan(
            decision.audit.video_id,
            (PlanStep.DRAFT, PlanStep.RENDER, PlanStep.QC, PlanStep.PUBLISH, PlanStep.MEASURE, PlanStep.LEARN),
            True,
        )
    if action == "COLLECT_MORE_DATA":
        return ExecutionPlan(
            decision.audit.video_id,
            (PlanStep.MEASURE, PlanStep.LEARN),
            False,
        )
    if action == "LEARN_FROM_RESULTS":
        return ExecutionPlan(
            decision.audit.video_id,
            (PlanStep.LEARN,),
            False,
        )
    return ExecutionPlan(decision.audit.video_id, (), False)
