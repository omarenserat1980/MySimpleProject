#!/usr/bin/env python3
"""Brain command contract.

Human-facing continuation phrases are normalized into explicit Brain commands.
The command authorizes continuation of the safe autonomous cycle; it never
authorizes bypassing verification, permissions, rollback, or evidence gates.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class BrainCommand:
    name: str
    source: str
    autonomous: bool = False


_CONTINUE = {
    "أكمل",
    "اكمل",
    "تابع",
    "استمر",
    "continue",
    "continue autonomously",
    "continue automatically",
    "keep going",
    "brain continue",
    "brain continue autonomously",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def parse(text: str) -> BrainCommand | None:
    normalized = normalize(text)
    if normalized in _CONTINUE:
        return BrainCommand(
            name="BRAIN_CONTINUE_AUTONOMOUSLY",
            source=text,
            autonomous=True,
        )
    return None


def is_continue(text: str) -> bool:
    command = parse(text)
    return bool(command and command.autonomous)


if __name__ == "__main__":
    import sys
    command = parse(" ".join(sys.argv[1:]))
    print(command.name if command else "NO_COMMAND")
