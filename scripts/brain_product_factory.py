import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(".brain_state")
strategy = json.loads((ROOT / "revenue_strategy.json").read_text())

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
}

selected_id = strategy["recommended_next"]
selected = PRODUCTS[selected_id]

plan = {
    "schema": "brain.product_factory_plan.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "strategy_id": selected_id,
    "product": selected,
    "stage": "BUILD_PLAN_READY",
    "financial_authority": "NONE",
    "external_publication": "BLOCKED",
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
        "build",
        "test",
        "quality_verify",
        "commercial_readiness",
        "external_publication_authorization",
        "payment_verification",
    ],
}

(ROOT / "product_factory_plan.json").write_text(
    json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
)

print(json.dumps(plan, ensure_ascii=False, indent=2))
