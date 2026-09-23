"""Promotion gate and recovery decisions."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class RecoveryDecision:
    promote:bool
    rollback:bool
    reason:str
def decide(tests_passed:bool,health_ok:bool,has_evidence:bool)->RecoveryDecision:
    if tests_passed and health_ok and has_evidence:
        return RecoveryDecision(True,False,"Evidence, tests and health checks passed.")
    return RecoveryDecision(False,True,"Promotion blocked until validation succeeds.")
