"""Evidence-backed, review-only gate for candidate capability promotion.

This gate evaluates supplied evidence. It never registers executors, probes
networks, executes generated code, or turns a candidate into an ONLINE node.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .software_capability_candidate_catalog import build_catalog

SCHEMA_VERSION = "brain-software-capability-promotion-gate/v1"
PASS = "PASS"


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def evaluate_promotion(
    capability_id: str,
    evidence: dict[str, Any],
    catalog: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
    max_age_hours: int = 24,
) -> dict[str, Any]:
    """Evaluate evidence against a catalog candidate; return eligibility only."""
    catalog = build_catalog() if catalog is None else catalog
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    candidates = {node.get("node_id"): node for node in catalog.get("nodes", [])}
    candidate = candidates.get(capability_id)
    reasons: list[str] = []
    if not isinstance(evidence, dict):
        evidence = {}
        reasons.append("INVALID_EVIDENCE_DOCUMENT")
    checks = evidence.get("checks", [])

    if candidate is None:
        reasons.append("CAPABILITY_NOT_IN_CATALOG")
        requirements: list[str] = []
    else:
        requirements = candidate.get("promotion_requirements", [])
        if candidate.get("candidate_state") in {"GAP", "BLOCKED_NEEDS_EVIDENCE", "UNCLASSIFIED_REQUIRES_REVIEW"}:
            reasons.append("CATALOG_STATE_REQUIRES_REVIEW")

    if not isinstance(evidence, dict) or evidence.get("schema") != "brain-capability-evidence/v1":
        reasons.append("INVALID_EVIDENCE_SCHEMA")
    if evidence.get("capability_id") != capability_id:
        reasons.append("CAPABILITY_ID_MISMATCH")
    if not isinstance(checks, list):
        checks = []
        reasons.append("CHECKS_MUST_BE_A_LIST")

    valid_by_requirement: dict[str, dict[str, Any]] = {}
    for item in checks:
        if not isinstance(item, dict):
            continue
        requirement = item.get("requirement")
        if isinstance(requirement, str) and requirement not in valid_by_requirement:
            valid_by_requirement[requirement] = item

    checked: list[dict[str, Any]] = []
    for requirement in requirements:
        item = valid_by_requirement.get(requirement)
        status = "MISSING"
        issue = "REQUIRED_EVIDENCE_MISSING"
        if item is not None:
            observed_at = _parse_time(item.get("observed_at"))
            ref = item.get("evidence_ref")
            if item.get("result") != PASS:
                status, issue = "FAIL", "CHECK_NOT_PASSED"
            elif not isinstance(ref, str) or not ref.strip():
                status, issue = "FAIL", "EVIDENCE_REFERENCE_MISSING"
            elif observed_at is None:
                status, issue = "FAIL", "INVALID_OBSERVATION_TIMESTAMP"
            elif observed_at > now:
                status, issue = "FAIL", "OBSERVATION_FROM_FUTURE"
            elif (now - observed_at).total_seconds() > max_age_hours * 3600:
                status, issue = "STALE", "EVIDENCE_TOO_OLD"
            else:
                status, issue = PASS, ""
        checked.append({"requirement": requirement, "status": status, "issue": issue})
        if status != PASS:
            reasons.append(f"{issue}:{requirement}")

    eligible = candidate is not None and not reasons and bool(requirements)
    return {
        "schema": SCHEMA_VERSION,
        "mode": "EVIDENCE_REVIEW_ONLY",
        "capability_id": capability_id,
        "decision": "ELIGIBLE_FOR_HUMAN_REVIEW" if eligible else "BLOCKED",
        "eligible_for_human_review": eligible,
        "automatic_registration_allowed": False,
        "executor_state": "NOT_REGISTERED",
        "capability_registry_mutated": False,
        "network_probed": False,
        "generated_code_executed": False,
        "max_evidence_age_hours": max_age_hours,
        "checks": checked,
        "reasons": reasons,
        "interpretation": (
            "Eligibility means only that the supplied evidence passed this gate. "
            "Human review and a separate authorized registration step are still required."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate capability evidence without registration")
    parser.add_argument("--capability-id", required=True)
    parser.add_argument("--evidence", required=True, help="path to brain-capability-evidence/v1 JSON")
    parser.add_argument("--output", help="write report to a new file; never overwrite")
    args = parser.parse_args(argv)
    evidence_path = Path(args.evidence)
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read valid evidence JSON: {exc}")
    report = evaluate_promotion(args.capability_id, evidence)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        destination = Path(args.output)
        if destination.exists():
            parser.error(f"refusing to overwrite existing file: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
    else:
        print(rendered, end="")
    return 0 if report["eligible_for_human_review"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
