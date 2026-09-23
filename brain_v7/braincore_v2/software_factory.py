"""Bounded software factory for the electronic brain."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class SoftwareSpec:
    name: str
    kind: str
    stack: tuple[str, ...]
    features: tuple[str, ...]
    output: str


SUPPORTED_KINDS = {"web", "api", "android", "desktop", "automation", "library"}


def plan_software(name: str, kind: str, stack: list[str] | tuple[str, ...],
                  features: list[str] | tuple[str, ...]) -> SoftwareSpec:
    kind = kind.lower().strip()
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"Unsupported software kind: {kind}")
    if not name.strip():
        raise ValueError("name must not be empty")
    return SoftwareSpec(name.strip(), kind, tuple(stack), tuple(features),
                        output=f"artifacts/software/{name.strip()}")


def implementation_stages(spec: SoftwareSpec) -> list[dict[str, Any]]:
    return [
        {"stage": "SPECIFY", "action": "define architecture and acceptance criteria"},
        {"stage": "SCAFFOLD", "action": "create project structure"},
        {"stage": "IMPLEMENT", "action": "build requested features"},
        {"stage": "INTEGRATE", "action": "connect APIs, storage and media providers"},
        {"stage": "VERIFY_LOCAL", "action": "inspect outputs and run available checks"},
        {"stage": "PACKAGE", "action": "prepare deployable artifact"},
        {"stage": "LEARN", "action": "record outcome and next improvement"},
    ]


def factory_snapshot() -> dict:
    return {
        "supported_kinds": sorted(SUPPORTED_KINDS),
        "external_deployment": False,
        "credential_access": False,
    }
