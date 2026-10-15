import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(".brain_state")
strategy = json.loads((ROOT / "revenue_strategy.json").read_text())

# Keep every strategy emitted by brain_revenue_strategy.py mapped to a safe
# planning record. This registry does not grant authority to spend or submit.
PRODUCTS = {
    "brain_owned_digital_product": {
        "product_id": "brain_digital_toolkit",
        "type": "digital_product",
        "build_cost_class": "LOW",
        "time_to_first_test": "SHORT",
        "repeatability": 0.90,
        "margin_potential": 0.90,
        "ownership": 1.00,
        "external_dependency": 0.25,
        "validation_method": "automated_build_and_quality_gate",
    },
    "brain_owned_game": {
        "product_id": "brain_game_factory_seed",
        "type": "game",
        "build_cost_class": "MEDIUM",
        "time_to_first_test": "MEDIUM",
        "repeatability": 0.95,
        "margin_potential": 0.85,
        "ownership": 1.00,
        "external_dependency": 0.35,
        "validation_method": "playable_build_and_smoke_test",
    },
    "micro_saas": {
        "product_id": "brain_micro_saas_seed",
        "type": "micro_saas",
        "build_cost_class": "MEDIUM",
        "time_to_first_test": "MEDIUM",
        "repeatability": 1.00,
        "margin_potential": 0.90,
        "ownership": 1.00,
        "external_dependency": 0.45,
        "validation_method": "local_api_test_and_contract_check",
    },
    "open_source_bounty": {
        "product_id": "brain_open_source_bounty_pipeline",
        "type": "opportunity_pipeline",
        "build_cost_class": "LOW",
        "time_to_first_test": "SHORT",
        "repeatability": 0.35,
        "margin_potential": 0.50,
        "ownership": 0.45,
        "external_dependency": 0.60,
        "validation_method": "repository_task_match_and_submission_readiness",
    },
    "sponsorship": {
        "product_id": "brain_sponsorship_readiness_pipeline",
        "type": "opportunity_pipeline",
        "build_cost_class": "LOW",
        "time_to_first_test": "MEDIUM",
        "repeatability": 0.70,
        "margin_potential": 0.60,
        "ownership": 0.80,
        "external_dependency": 0.70,
        "validation_method": "audience_evidence_and_sponsor_fit_review",
    },
    "free_ai_demo": {
        "product_id": "brain_free_ai_demo",
        "type": "digital_demo",
        "build_cost_class": "LOW",
        "time_to_first_test": "SHORT",
        "repeatability": 0.60,
        "margin_potential": 0.50,
        "ownership": 0.60,
        "external_dependency": 0.50,
        "validation_method": "local_demo_smoke_test_and_quality_gate",
    },
}

selected_id = strategy.get("recommended_next")
selected = PRODUCTS.get(selected_id)
if selected is None:
    supported = ", ".join(sorted(PRODUCTS))
    raise SystemExit(
        f"UNSUPPORTED_RECOMMENDED_STRATEGY: {selected_id!r}. "
        f"Add a matching factory plan first. Supported strategies: {supported}"
    )

plan = {
    "schema": "brain.product_factory_plan.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "strategy_id": selected_id,
    "product": selected,
    "stage": "BUILD_PLAN_READY",
    "financial_authority": "NONE",
    "external_publication": "BLOCKED",
    "external_submission": "BLOCKED",
    "payment": "NOT_VERIFIED",
    "quality_gate_required": True,
    "cost_tracking": {
        "money_spent": 0,
        "currency": None,
        "measurement": "INTERNAL_EFFORT_ONLY_UNTIL_REAL_COST_EVIDENCE_EXISTS",
    },
    "revenue_forecast": {
        "status": "FORECAST_ONLY",
        "counts_as_revenue": False,
    },
    "gates": [
        "build_or_prepare",
        "test",
        "quality_verify",
        "commercial_readiness",
        "external_publication_authorization",
        "external_submission_authorization",
        "payment_verification",
    ],
}

ROOT.mkdir(exist_ok=True)
(ROOT / "product_factory_plan.json").write_text(
    json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
)

print(json.dumps(plan, ensure_ascii=False, indent=2))
