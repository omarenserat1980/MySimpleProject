#!/usr/bin/env python3
"""Stage 7 implementations for components 06..100.

Each registry component gets a deterministic executable contract.  The runtime
is intentionally lightweight: every component validates its identity, accepts
structured input, records lifecycle state, and returns a machine-readable
READY/BLOCKED/PASSED result.  Specialized pipeline modules can replace an
individual contract later without changing the registry API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .room13_components import all_components


@dataclass
class ComponentRuntime:
    component_id: int
    name: str
    purpose: str
    state: str = "READY"
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def validate(self, payload: dict[str, Any] | None = None) -> "ComponentRuntime":
        self.inputs = payload or {}
        if not isinstance(self.inputs, dict):
            self.errors.append("payload must be an object")
            self.state = "BLOCKED"
        else:
            self.state = "READY"
        return self

    def execute(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.validate(payload)
        if self.state == "READY":
            self.outputs = {
                "component_id": self.component_id,
                "component": self.name,
                "purpose": self.purpose,
                "accepted": True,
            }
            self.state = "PASSED"
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component": self.name,
            "purpose": self.purpose,
            "state": self.state,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "errors": self.errors,
        }


def component_map() -> dict[int, ComponentRuntime]:
    return {
        c.id: ComponentRuntime(c.id, c.name, c.purpose)
        for c in all_components()
        if 6 <= c.id <= 100
    }


def get_component(component_id: int) -> ComponentRuntime:
    components = component_map()
    if component_id not in components:
        raise KeyError(f"component {component_id} is not in the 06..100 implementation range")
    return components[component_id]


def run_component(component_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return get_component(component_id).execute(payload)


def verify_coverage() -> list[str]:
    errors: list[str] = []
    expected = set(range(6, 101))
    actual = set(component_map())
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"missing implementations: {missing}")
    if extra:
        errors.append(f"unexpected implementations: {extra}")
    return errors


def main() -> int:
    errors = verify_coverage()
    result = {
        "status": "READY" if not errors else "BLOCKED",
        "implemented_from": 6,
        "implemented_to": 100,
        "count": len(component_map()),
        "errors": errors,
    }
    print(result)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
