from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class Workflow:
    name: str
    steps: tuple[WorkflowStep, ...]


def load(path: Path) -> Workflow:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("name"), str):
        raise ValueError("workflow manifest requires a name")
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("workflow manifest requires steps")

    steps: list[WorkflowStep] = []
    for item in raw_steps:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("workflow step requires a name")
        command = item.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            raise ValueError("workflow step command must be a non-empty string list")
        steps.append(WorkflowStep(item["name"], tuple(command)))
    return Workflow(data["name"], tuple(steps))
