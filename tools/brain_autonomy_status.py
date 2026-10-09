#!/usr/bin/env python3
"""Single source of truth for Brain's live autonomy status.

No configuration flag can grant autonomy.  The status is derived from the
durable independence proof plus the currently live Brain-owned executor.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make direct execution from tools/ work without requiring PYTHONPATH.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from platform_foundation.brain_execution_authority import BrainExecutionAuthority
from platform_foundation.independence_contract import IndependenceContract
PROOF = ROOT / "brain6_artifacts" / "independence_gate" / "independence_proof.json"


def evaluate() -> dict[str, object]:
    contract = IndependenceContract(PROOF).evaluate()
    authority = BrainExecutionAuthority().readiness()
    proof_ok = bool(contract.get("allowed"))
    authority_ok = bool(authority.get("ready"))
    autonomous = proof_ok and authority_ok
    if autonomous:
        status = "AUTONOMOUS_WITHIN_AUTHORITY"
        reason = "scoped_proof_and_live_brain_executor_ready"
    elif not proof_ok:
        status = "NOT_AUTONOMOUS"
        reason = f"independence_contract:{contract.get('reason', 'rejected')}"
    else:
        status = "NOT_AUTONOMOUS"
        reason = f"live_executor:{authority.get('reason', 'not_ready')}"
    return {
        "schema": "brain.autonomy_status.v1",
        "status": status,
        "reason": reason,
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
