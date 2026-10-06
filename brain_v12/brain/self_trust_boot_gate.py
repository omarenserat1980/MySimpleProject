from __future__ import annotations

"""Deterministic boot gate for the Brain self-trust bootstrap chain."""

from dataclasses import dataclass
from pathlib import Path

BOOT_GATE_VERSION = "BRAIN-SELF-TRUST-GATE-1"
BOOTSTRAP_CAPABILITY = "brain_self_test"


@dataclass(frozen=True)
class BootGateEvidence:
    trust_root_present: bool
    runtime_ready: bool
    agent_online: bool
    self_test_verified: bool
    task_id: str = ""


@dataclass(frozen=True)
class BootGateResult:
    ok: bool
    status: str
    gate: str
    capability: str
    task_id: str
    failed_checks: tuple[str, ...]


def default_trust_root(path: str | None = None) -> Path:
    return Path(path or "~/v12-agent/agent.key").expanduser()


def evaluate(evidence: BootGateEvidence) -> BootGateResult:
    failed: list[str] = []
    if not evidence.trust_root_present:
        failed.append("TRUST_ROOT_MISSING")
    if not evidence.runtime_ready:
        failed.append("RUNTIME_NOT_READY")
    if not evidence.agent_online:
        failed.append("AGENT_OFFLINE")
    if not evidence.self_test_verified:
        failed.append("SELF_TEST_NOT_VERIFIED")
    return BootGateResult(
        ok=not failed,
        status="BRAIN_READY" if not failed else "BRAIN_BOOT_BLOCKED",
        gate=BOOT_GATE_VERSION,
        capability=BOOTSTRAP_CAPABILITY,
        task_id=evidence.task_id,
        failed_checks=tuple(failed),
    )


def evaluate_from_observations(*, runtime_ready: bool, agent_online: bool,
                                self_test_verified: bool, task_id: str = "",
                                trust_root: str | None = None) -> BootGateResult:
    return evaluate(BootGateEvidence(
        trust_root_present=default_trust_root(trust_root).is_file(),
        runtime_ready=runtime_ready,
        agent_online=agent_online,
        self_test_verified=self_test_verified,
        task_id=task_id,
    ))
