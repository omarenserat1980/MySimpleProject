#!/usr/bin/env python3
"""Single source of truth for Brain's live autonomy status.

No configuration flag can grant autonomy.  The status is derived from the
durable independence proof plus the currently live Brain-owned executor.
"""
from __future__ import annotations

import json
from pathlib import Path

from platform_foundation.brain_execution_authority import BrainExecutionAuthority
from platform_foundation.independence_contract import IndependenceContract

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "brain6_artifacts" / "independence_gate" / "independence_proof.json"


def evaluate() -> dict[str, object]:
    contract = IndependenceContract(PROOF).evaluate()
    authority = BrainExecutionAuthority().readiness()
    autonomous = bool(contract.get("allowed")) and bool(authority.get("ready"))
    return {
        "schema": "brain.autonomy_status.v1",
        "AUTONOMOUS_WITHIN_AUTHORITY": autonomous,
        "scoped_independence_proven": bool(contract.get("allowed")),
        "live_brain_executor_ready": bool(authority.get("ready")),
        "contract": contract,
        "authority": authority,
        "rule": "proof_and_live_authority_required",
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["AUTONOMOUS_WITHIN_AUTHORITY"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
