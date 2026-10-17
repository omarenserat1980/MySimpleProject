"""Safe stage discovery for APM BUILD.

Discovery extracts declared stage definitions without inventing unsafe
parallelism. A plain ordered sequence becomes a dependency chain. Parallelism
requires explicit dependency metadata or an explicit independent policy.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .parallel_stage_scheduler import Stage


@dataclass(frozen=True)
class StageDiscovery:
    source: str
    stages: tuple[Stage, ...]
    policy: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "policy": self.policy,
            "stage_count": len(self.stages),
            "stages": [
                {
                    "id": stage.id,
                    "depends_on": list(stage.depends_on),
                    "resource": stage.resource,
                    "metadata": dict(stage.metadata),
                }
                for stage in self.stages
            ],
        }


def from_sequence(
    sequence: Iterable[str | tuple[str, str]],
    *,
    source: str = "declared_sequence",
    policy: str = "sequential",
) -> StageDiscovery:
    """Convert an ordered declaration into safe Stage objects.

    "sequential" preserves original semantics. "independent" is intentionally
    opt-in and should only be used when the caller knows stages are independent.
    """
    if policy not in {"sequential", "independent"}:
        raise ValueError("policy must be sequential or independent")

    normalized: list[tuple[str, str]] = []
    for item in sequence:
        if isinstance(item, tuple):
            stage_id, label = item
        else:
            stage_id, label = str(item), str(item)
        normalized.append((str(stage_id), str(label)))

    stages: list[Stage] = []
    previous: str | None = None
    for stage_id, label in normalized:
        dependencies = () if policy == "independent" else (
            (previous,) if previous is not None else ()
        )
        stages.append(
            Stage(
                id=stage_id,
                depends_on=dependencies,
                metadata={"label": label, "source": source},
            )
        )
        previous = stage_id

    return StageDiscovery(source=source, stages=tuple(stages), policy=policy)


def from_mapping(
    declarations: Iterable[Mapping[str, Any]],
    *,
    source: str = "explicit_mapping",
) -> StageDiscovery:
    """Build stages from explicit dependency/resource declarations."""
    stages: list[Stage] = []
    for item in declarations:
        stage_id = str(item["id"])
        dependencies = tuple(str(value) for value in item.get("depends_on", ()))
        stages.append(
            Stage(
                id=stage_id,
                depends_on=dependencies,
                resource=item.get("resource"),
                input_fingerprint=str(item.get("input_fingerprint", "")),
                metadata=dict(item.get("metadata", {})),
            )
        )
    return StageDiscovery(source=source, stages=tuple(stages), policy="explicit")


def from_module(
    module_name: str,
    *,
    attribute: str = "STAGES",
    policy: str = "sequential",
) -> StageDiscovery:
    """Discover a declared STAGES sequence from a Brain module."""
    module = importlib.import_module(module_name)
    sequence = getattr(module, attribute, None)
    if sequence is None:
        raise ValueError(f"{module_name}.{attribute} not found")
    return from_sequence(sequence, source=f"{module_name}.{attribute}", policy=policy)
