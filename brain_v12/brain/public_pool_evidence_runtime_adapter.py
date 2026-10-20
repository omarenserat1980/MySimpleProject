"""Read-only adapter from persisted Public Pool diagnostics to Brain classification.

This adapter reads local artifacts only. It performs no network calls, never starts
or stops a miner, does not modify pool settings, and never establishes revenue.
It is an explicit CLI/callable integration point, not an always-on service hook.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from brain_v12.brain.public_pool_local_evidence import classify_public_pool_evidence

MAX_INPUT_BYTES = 1_048_576


def _read_bounded(path: str | Path) -> bytes:
    target = Path(path)
    with target.open("rb") as handle:
        data = handle.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("INPUT_EXCEEDS_1_MIB_LIMIT")
    return data


def evaluate_persisted_public_pool_evidence(
    *, miner_log_path: str | Path | None = None,
    pool_snapshot_path: str | Path | None = None,
) -> dict[str, Any]:
    """Classify existing local artifacts; missing artifacts remain unknown."""
    miner_log = ""
    pool_snapshot: dict[str, Any] | None = None
    input_hashes: dict[str, str] = {}

    if miner_log_path is not None:
        raw_log = _read_bounded(miner_log_path)
        miner_log = raw_log.decode("utf-8", errors="replace")
        input_hashes["miner_log_sha256"] = hashlib.sha256(raw_log).hexdigest()

    if pool_snapshot_path is not None:
        raw_snapshot = _read_bounded(pool_snapshot_path)
        input_hashes["pool_snapshot_sha256"] = hashlib.sha256(raw_snapshot).hexdigest()
        try:
            parsed = json.loads(raw_snapshot)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("POOL_SNAPSHOT_MUST_BE_JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("POOL_SNAPSHOT_MUST_BE_JSON_OBJECT")
        pool_snapshot = parsed

    result = classify_public_pool_evidence(
        miner_log=miner_log,
        pool_snapshot=pool_snapshot,
    )
    result["adapter"] = "persisted_public_pool_evidence_v1"
    result["input_artifact_sha256"] = input_hashes
    result["network_access_performed"] = False
    result["miner_started_or_stopped"] = False
    result["pool_settings_changed"] = False
    result["revenue_verified"] = False
    result["payout_verified"] = False
    result["brain_runtime_activity_verified"] = False
    return result


def persist_public_pool_evidence(
    evidence_store: Any,
    task_id: str,
    *,
    miner_log_path: str | Path | None = None,
    pool_snapshot_path: str | Path | None = None,
    mission_id: str | None = None,
    attempt: int | None = None,
    phase: str | None = None,
) -> dict[str, Any]:
    """Persist a classification of existing local artifacts as unverified evidence.

    This is an explicit call site, not a background poller. It only reads the
    paths supplied by the caller and appends one diagnostic record. EvidenceStore
    integrity verification must not be interpreted as proof of shares, payout,
    revenue, or attribution to a Brain process.
    """
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    report = evaluate_persisted_public_pool_evidence(
        miner_log_path=miner_log_path,
        pool_snapshot_path=pool_snapshot_path,
    )
    item = evidence_store.append(
        task_id.strip(),
        "public_pool_diagnostic",
        report,
        producer="brain.public_pool_evidence_runtime_adapter",
        mission_id=mission_id,
        attempt=attempt,
        phase=phase,
    )
    return {
        "evidence_id": item["evidence_id"],
        "task_id": item["task_id"],
        "kind": item["kind"],
        "verification_status": item["verification_status"],
        "sha256": item["sha256"],
        "report": item["payload"],
        "revenue_verified": False,
        "payout_verified": False,
        "financial_execution_enabled": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--miner-log", help="Existing local miner log; read only")
    parser.add_argument("--pool-snapshot", help="Existing JSON snapshot from the read-only collector")
    args = parser.parse_args()
    try:
        result = evaluate_persisted_public_pool_evidence(
            miner_log_path=args.miner_log,
            pool_snapshot_path=args.pool_snapshot,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "reason": str(exc),
            "network_access_performed": False,
            "miner_started_or_stopped": False,
            "pool_settings_changed": False,
            "revenue_verified": False,
            "payout_verified": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
