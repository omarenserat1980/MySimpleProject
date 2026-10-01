#!/usr/bin/env python3
"""Brain command contract.

The Brain owns the human command vocabulary. "أكمل" is a first-class
Brain command, not a UI-specific shortcut. Human-facing continuation phrases
are normalized into the canonical Brain command.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class BrainCommand:
    name: str
    source: str
    autonomous: bool = False


# Canonical commands owned by the Brain.
BRAIN_CONTINUE_AUTONOMOUSLY = "BRAIN_CONTINUE_AUTONOMOUSLY"

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
            name=BRAIN_CONTINUE_AUTONOMOUSLY,
            source=text,
            autonomous=True,
        )
    return None


def command_name(text: str) -> str | None:
    """Return the canonical Brain command name for human input."""
    command = parse(text)
    return command.name if command else None


def is_continue(text: str) -> bool:
    command = parse(text)
    return bool(command and command.autonomous)


if __name__ == "__main__":
    import sys
    command = parse(" ".join(sys.argv[1:]))
    print(command.name if command else "NO_COMMAND")
