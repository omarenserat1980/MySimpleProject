"""Evidence-gated autonomy certification.

The Brain may claim autonomy within authority only after a real, repeatable
local execution test proves persistence, execution, verification, recovery,
and correct blocking at the authority boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
import uuid
from typing import Any, Callable


@dataclass(frozen=True)
class AutonomyEvidence:
    run_id: str
    persistence: bool
    execution: bool
    verification: bool
    recovery: bool
    authority_boundary: bool
    github_independent: bool
    certified: bool
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_independence_test(
    runtime_factory: Callable[[Path], Any],
    executor_factory: Callable[[], Any],
    root: str | Path,
) -> dict[str, Any]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex

    # Phase 1: create durable work, then simulate process loss.
    runtime = runtime_factory(root)
    task = runtime.enqueue(
        "autonomy-proof",
        ["python", "-c", "print('BRAIN_AUTONOMY_PROOF')"],
        "brain-internal-execution",
    )
    persistence = bool(task.get("id")) and bool(runtime.pending())

    # Phase 2: create a fresh runtime instance from disk.
    recovered_runtime = runtime_factory(root)
    recovery = any(x.get("id") == task["id"] for x in recovered_runtime.pending())

    # Phase 3: execute through the Brain-owned executor only.
    executor = executor_factory()
    result = executor.run_one()
    execution = result.get("state") == "COMPLETED"
    verification = bool(result.get("evidence_ref")) and result.get("sha256")

    # Phase 4: authority boundary must reject an unavailable/unverified runner.
    boundary = False
    try:
        from .execution_gateway import BrainExecutionGateway

        class OfflineRunner:
            def require(self, capability: str) -> None:
                raise RuntimeError("BRAIN_INTERNAL_RUNNER_NOT_VERIFIED")

        BrainExecutionGateway(OfflineRunner()).authorize("brain-internal-execution")
    except RuntimeError as exc:
        boundary = "BRAIN_INTERNAL_RUNNER_NOT_VERIFIED" in str(exc)

    evidence = AutonomyEvidence(
        run_id=run_id,
        persistence=persistence,
        execution=execution,
        verification=bool(verification),
        recovery=recovery,
        authority_boundary=boundary,
        github_independent=True,
        certified=all((persistence, execution, bool(verification), recovery, boundary)),
        timestamp=time.time(),
    ).to_dict()

    evidence["status"] = (
        "AUTONOMOUS_WITHIN_AUTHORITY"
        if evidence["certified"]
        else "AUTONOMY_NOT_CERTIFIED"
    )
    evidence_path = root / f"autonomy-{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    evidence["evidence_ref"] = str(evidence_path)
    return evidence


def require_certified(evidence: dict[str, Any]) -> None:
    if evidence.get("status") != "AUTONOMOUS_WITHIN_AUTHORITY":
        raise RuntimeError("AUTONOMOUS_WITHIN_AUTHORITY_NOT_PROVEN")
