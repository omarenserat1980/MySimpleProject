"""Reality-first completion gate for Electronic Brain.

A process finishing is not success. Delivery is allowed only when the desired
world-state, invariants, and required evidence are verified.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

class CompletionState(str, Enum):
    UNKNOWN="UNKNOWN"; TREATMENT_REQUIRED="TREATMENT_REQUIRED"
    VERIFYING="VERIFYING"; VERIFIED_COMPLETED="VERIFIED_COMPLETED"
    BLOCKED_EXTERNAL="BLOCKED_EXTERNAL"

@dataclass
class CompletionContract:
    desired: Mapping[str, Any]
    invariants: Mapping[str, Any] = field(default_factory=dict)
    evidence_required: bool = True

class ProblemCompletionGate:
    def __init__(self, contract: CompletionContract):
        self.contract=contract
        self.state=CompletionState.UNKNOWN
        self.diagnostic_depth=0
        self.history=[]

    @staticmethod
    def _matches(expected, actual):
        if isinstance(expected, Mapping):
            return isinstance(actual, Mapping) and all(
                k in actual and ProblemCompletionGate._matches(v, actual[k])
                for k,v in expected.items())
        if isinstance(expected,(list,tuple,set)):
            return isinstance(actual,(list,tuple,set)) and all(x in actual for x in expected)
        return expected == actual

    def observe(self, verified_world, evidence=None):
        missing=[k for k,v in self.contract.desired.items()
                 if k not in verified_world or not self._matches(v,verified_world[k])]
        violated=[k for k,v in self.contract.invariants.items()
                   if k not in verified_world or not self._matches(v,verified_world[k])]
        evidence_ok=(not self.contract.evidence_required) or bool(evidence and evidence.get("verified"))
        delta={"missing":missing,"violated_invariants":violated,"evidence_valid":evidence_ok}
        if not missing and not violated and evidence_ok:
            self.state=CompletionState.VERIFIED_COMPLETED
        else:
            self.state=CompletionState.TREATMENT_REQUIRED
            self.diagnostic_depth=0
        self.history.append({"state":self.state.value,"delta":delta})
        return delta

    def decision(self, verified_world, evidence=None):
        delta=self.observe(verified_world,evidence)
        if self.state==CompletionState.VERIFIED_COMPLETED:
            return {"action":"deliver","reason":"desired_world_state_verified","delta":delta}
        return {"action":"treat","reason":"reality_delta_remains","reset_diagnostic_depth":True,"delta":delta}
