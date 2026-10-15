"""Evidence-gated lifecycle for Brain tools: simulate, build real, verify, then activate.

This module orchestrates a lifecycle; it does not pretend to supply external
connectors, credentials, hardware, or permissions that a concrete tool lacks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping


class ToolState(str, Enum):
    CREATED = "CREATED"
    SIMULATING = "SIMULATING"
    SIMULATION_PASSED = "SIMULATION_PASSED"
    BUILDING_REAL = "BUILDING_REAL"
    REAL_BUILT = "REAL_BUILT"
    VERIFYING_REAL = "VERIFYING_REAL"
    REAL_VERIFIED = "REAL_VERIFIED"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass
class ToolLifecycleResult:
    tool_name: str
    state: ToolState = ToolState.CREATED
    history: list[str] = field(default_factory=lambda: [ToolState.CREATED.value])
    evidence: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None

    def transition(self, state: ToolState) -> None:
        self.state = state
        self.history.append(state.value)


class LifecycleError(RuntimeError):
    """Raised when a tool cannot safely advance to the next lifecycle state."""


def build_and_verify_tool(
    *,
    tool_name: str,
    simulate: Callable[[], bool],
    build_real: Callable[[], Any],
    verify_real: Callable[[Any], Mapping[str, Any]],
    activate: Callable[[Any], Any] | None = None,
    activation_authorized: bool = False,
) -> ToolLifecycleResult:
    """Run simulation, immediately build the real adapter, then verify it.

    A failed simulation prevents real construction. A failed or empty real
    evidence result prevents REAL_VERIFIED/ACTIVE. Activation is optional and
    requires an explicit authorization flag; the real build itself begins
    immediately after a passing simulation.
    """
    result = ToolLifecycleResult(tool_name=tool_name)
    try:
        result.transition(ToolState.SIMULATING)
        if simulate() is not True:
            result.reason = "Simulation did not return literal True."
            result.transition(ToolState.BLOCKED)
            return result

        result.transition(ToolState.SIMULATION_PASSED)
        result.transition(ToolState.BUILDING_REAL)
        implementation = build_real()
        if implementation is None:
            result.reason = "Real implementation builder returned None."
            result.transition(ToolState.BLOCKED)
            return result

        result.transition(ToolState.REAL_BUILT)
        result.transition(ToolState.VERIFYING_REAL)
        evidence = verify_real(implementation)
        if not isinstance(evidence, Mapping) or not evidence:
            result.reason = "Real verification produced no evidence."
            result.transition(ToolState.BLOCKED)
            return result
        if evidence.get("verified") is not True:
            result.evidence = dict(evidence)
            result.reason = "Real verification did not affirm verified=True."
            result.transition(ToolState.BLOCKED)
            return result

        result.evidence = dict(evidence)
        result.transition(ToolState.REAL_VERIFIED)

        if activate is not None:
            if not activation_authorized:
                result.reason = "Real implementation verified; activation requires authorization."
                result.transition(ToolState.BLOCKED)
                return result
            activation_result = activate(implementation)
            if activation_result is not True:
                result.reason = "Activation did not return literal True."
                result.transition(ToolState.BLOCKED)
                return result
            result.transition(ToolState.ACTIVE)
        return result
    except Exception as exc:
        result.reason = f"{type(exc).__name__}: {exc}"
        result.transition(ToolState.FAILED)
        return result
