from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CommandSpec:
    command: list[str]
    timeout_seconds: int = 900

@dataclass(frozen=True)
class StageSpec:
    id: str
    name: str
    run: CommandSpec
    verify: CommandSpec
    repair: tuple[CommandSpec, ...] = ()
    rollback: CommandSpec | None = None
    repair_allowed: bool = False
    max_retries: int = 2
    dependencies: tuple[str, ...] = ()
    enabled: bool = True
    verify_wait_seconds: int = 0

@dataclass
class StageResult:
    stage_id: str
    status: str
    attempts: int
    repairs: int
    started_at: str
    finished_at: str
    last_result: dict[str, Any] = field(default_factory=dict)
    evidence_path: str = ""

@dataclass
class PipelineState:
    schema_version: str
    pipeline_id: str
    status: str
    total_stages: int
    current_stage: str | None
    current_step: str
    completed_stages: list[str]
    failed_stages: list[str]
    blocked_stages: list[str]
    attempt: int
    commit_sha: str
    last_result: dict[str, Any]
    updated_at: str
