"""Closed-loop earning cycle planner.

Connects opportunity discovery, delivery evidence, payment readiness and
post-payment learning into one bounded state machine. It never submits jobs or
moves money itself.
"""
from dataclasses import dataclass
from enum import Enum

class Stage(str, Enum):
    DISCOVER="DISCOVER"; QUALIFY="QUALIFY"; PREPARE="PREPARE"; USER_SUBMISSION="USER_SUBMISSION"
    DELIVER="DELIVER"; PAYMENT_PENDING="PAYMENT_PENDING"; VERIFY="VERIFY"; LEARN="LEARN"

@dataclass(frozen=True)
class CycleDecision:
    stage: Stage
    next_action: str
    reason: str
    requires_user_action: bool

def next_stage(*, has_evidence: bool, fit_ok: bool, risk_ok: bool,
               ready_for_submission: bool, delivered: bool,
               payment_verified: bool, result_recorded: bool) -> CycleDecision:
    if not has_evidence: return CycleDecision(Stage.DISCOVER,"RESEARCH","Evidence is missing.",False)
    if not fit_ok: return CycleDecision(Stage.QUALIFY,"REJECT","Opportunity fit is below threshold.",False)
    if not risk_ok: return CycleDecision(Stage.QUALIFY,"REVIEW","Risk requires review.",True)
    if not ready_for_submission: return CycleDecision(Stage.PREPARE,"PREPARE_PROPOSAL","Prepare a bounded deliverable.",False)
    if not delivered: return CycleDecision(Stage.USER_SUBMISSION,"SUBMIT","User submission/authorization is required.",True)
    if not payment_verified: return CycleDecision(Stage.PAYMENT_PENDING,"WAIT_FOR_PROVIDER_CONFIRMATION","Await provider evidence.",False)
    if not result_recorded: return CycleDecision(Stage.VERIFY,"RECORD_OUTCOME","Record verified result and evidence.",False)
    return CycleDecision(Stage.LEARN,"LEARN_AND_OPTIMIZE","Feed verified outcome back into ranking.",False)
