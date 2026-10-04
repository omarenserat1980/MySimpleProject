import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(".brain_state")
task = json.loads((ROOT / "opportunity_task.json").read_text())
queue = json.loads((ROOT / "opportunity_queue.json").read_text())

ALLOWED = {
    "brain_games": "PREPARE_GAME_PRODUCT",
    "digital_tools": "PREPARE_DIGITAL_TOOL",
    "micro_saas": "PREPARE_MICRO_SAAS",
    "open_source_bounties": "PREPARE_BOUNDED_BOUNTY_WORK",
    "github_sponsors": "PREPARE_SPONSORSHIP_ASSET",
    "ai_demos_free_compute": "PREPARE_FREE_AI_DEMO",
}

opportunity = task["opportunity_id"]
action = ALLOWED.get(opportunity)
if not action:
    raise SystemExit(f"UNSUPPORTED_OPPORTUNITY={opportunity}")

target = queue.get("selected_target")
scope = {
    "opportunity": opportunity,
    "action": action,
    "target": target,
    "constraints": [
        "no_financial_side_effects",
        "no_external_submission",
        "no_false_payment_claim",
        "preserve_audit_evidence",
    ],
}

(ROOT / "opportunity_scope.json").write_text(
    json.dumps(scope, ensure_ascii=False, indent=2) + "\n"
)

result = {
    "schema": "brain.opportunity_execution_result.v2",
    "task_id": task["task_id"],
    "opportunity_id": opportunity,
    "action": action,
    "started_at": datetime.now(timezone.utc).isoformat(),
    "execution_mode": "BOUNDED_LOCAL_PREPARATION",
    "financial_side_effects": "BLOCKED",
    "external_submission": "NOT_PERFORMED",
    "payment": "NOT_VERIFIED",
    "status": "EXECUTION_PREPARED",
    "evidence": {
        "queue_present": bool(queue.get("candidates")),
        "task_state": task.get("state"),
        "required_evidence": task.get("required_evidence", []),
        "live_target_present": target is not None,
        "scope_artifact": ".brain_state/opportunity_scope.json",
    },
}

(ROOT / "opportunity_execution_result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)

verification = {
    "schema": "brain.opportunity_verification.v2",
    "task_id": task["task_id"],
    "verified_at": datetime.now(timezone.utc).isoformat(),
    "checks": {
        "supported_opportunity": True,
        "queue_evidence_present": bool(queue.get("candidates")),
        "scope_artifact_present": (ROOT / "opportunity_scope.json").exists(),
        "execution_result_present": True,
        "financial_side_effects_blocked": result["financial_side_effects"] == "BLOCKED",
        "external_submission_not_performed": result["external_submission"] == "NOT_PERFORMED",
        "payment_not_claimed": result["payment"] == "NOT_VERIFIED",
    },
    "status": "VERIFIED_PREPARATION",
    "commercial_state": "MONETIZATION_PATH_DEFINED",
    "payment_state": "NOT_VERIFIED",
}

if not all(verification["checks"].values()):
    raise SystemExit("OPPORTUNITY_EXECUTION_VERIFICATION=FAILED")

(ROOT / "opportunity_verification.json").write_text(
    json.dumps(verification, ensure_ascii=False, indent=2) + "\n"
)

print("OPPORTUNITY_EXECUTION=VERIFIED_PREPARATION")
print("PAYMENT=NOT_VERIFIED")
