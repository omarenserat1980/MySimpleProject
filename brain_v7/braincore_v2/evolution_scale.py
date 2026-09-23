"""Scalable evolution accounting up to 100,000,000,000 milestones.

This is a compact state machine rather than materializing 100 billion records.
A milestone is promoted only after evidence. The engine does not grant
permissions, deploy itself, submit external jobs, or move money.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

MAX_GENERATION = 100_000_000_000


@dataclass(frozen=True)
class EvolutionState:
    generation: int
    target: int = MAX_GENERATION
    evidence_verified: bool = False
    autonomous_side_effects: bool = False


def validate_generation(generation: int) -> int:
    if not 1 <= generation <= MAX_GENERATION:
        raise ValueError(f"generation must be within 1..{MAX_GENERATION}")
    return generation


def next_generation(completed: Iterable[int] = ()) -> int | None:
    done = {int(x) for x in completed if 1 <= int(x) <= MAX_GENERATION}
    for generation in range(1, min(max(done, default=0) + 2, MAX_GENERATION + 1)):
        if generation not in done:
            return generation
    if len(done) >= MAX_GENERATION:
        return None
    return max(done, default=0) + 1


def promote(generation: int, passed: bool, evidence: str) -> EvolutionState:
    generation = validate_generation(generation)
    if not passed or not evidence.strip():
        return EvolutionState(generation=generation)
    return EvolutionState(
        generation=generation,
        evidence_verified=True,
        autonomous_side_effects=False,
    )


def progress(generation: int) -> dict:
    generation = max(0, min(MAX_GENERATION, int(generation)))
    return {
        "generation": generation,
        "target": MAX_GENERATION,
        "remaining": MAX_GENERATION - generation,
        "progress_fraction": generation / MAX_GENERATION,
        "progress_percent": generation / MAX_GENERATION * 100,
        "requires_evidence": True,
        "autonomous_side_effects": False,
    }
