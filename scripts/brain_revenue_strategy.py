import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(".brain_state")

# Strategy scores effort allocation only. It never authorizes spending,
# contracts, withdrawals, purchases, or external submissions.
STRATEGIES = [
    {
        "id": "brain_owned_digital_product",
        "family": "BRAIN_OWNED",
        "return_score": 8,
        "success_score": 0.30,
        "evidence_score": 0.85,
        "speed_score": 0.75,
        "scalability_score": 0.90,
        "ownership_score": 1.00,
        "risk": 1,
        "cost": 0,
        "complexity": 4,
    },
    {
        "id": "brain_owned_game",
        "family": "BRAIN_OWNED",
        "return_score": 9,
        "success_score": 0.20,
        "evidence_score": 0.80,
        "speed_score": 0.55,
        "scalability_score": 0.95,
        "ownership_score": 1.00,
        "risk": 2,
        "cost": 0,
        "complexity": 5,
    },
    {
        "id": "micro_saas",
        "family": "BRAIN_OWNED",
        "return_score": 10,
        "success_score": 0.15,
        "evidence_score": 0.80,
        "speed_score": 0.40,
        "scalability_score": 1.00,
        "ownership_score": 1.00,
        "risk": 2,
        "cost": 0,
        "complexity": 6,
    },
    {
        "id": "open_source_bounty",
        "family": "FREE_DIVERSE",
        "return_score": 8,
        "success_score": 0.35,
        "evidence_score": 0.90,
        "speed_score": 0.80,
        "scalability_score": 0.35,
        "ownership_score": 0.45,
        "risk": 1,
        "cost": 0,
        "complexity": 3,
    },
    {
        "id": "sponsorship",
        "family": "FREE_DIVERSE",
        "return_score": 7,
        "success_score": 0.12,
        "evidence_score": 0.95,
        "speed_score": 0.25,
        "scalability_score": 0.70,
        "ownership_score": 0.80,
        "risk": 1,
        "cost": 0,
        "complexity": 2,
    },
    {
        "id": "free_ai_demo",
        "family": "FREE_DIVERSE",
        "return_score": 7,
        "success_score": 0.18,
        "evidence_score": 0.80,
        "speed_score": 0.65,
        "scalability_score": 0.60,
        "ownership_score": 0.60,
        "risk": 2,
        "cost": 0,
        "complexity": 4,
    },
]

def strategy_score(s):
    base = (
        s["return_score"]
        * s["success_score"]
        * s["evidence_score"]
        * (0.30 + 0.20 * s["speed_score"]
           + 0.25 * s["scalability_score"]
           + 0.25 * s["ownership_score"])
    )
    penalty = max(1, s["risk"] + s["cost"] + s["complexity"])
    return round(base / penalty, 6)

for s in STRATEGIES:
    s["strategy_score"] = strategy_score(s)

STRATEGIES.sort(key=lambda x: x["strategy_score"], reverse=True)

policy = {
    "schema": "brain.revenue_strategy.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "objective": "MAXIMIZE_EXPECTED_NET_VALUE_WITH_EVIDENCE_AND_BOUNDED_RISK",
    "effort_only": True,
    "financial_authority": "NONE",
    "external_side_effects": "BLOCKED",
    "paid_external": "DISABLED_BY_DEFAULT",
    "commercial_truth": "PAYMENT_VERIFIED_REQUIRED",
    "principles": [
        "Prefer_brain_owned_assets",
        "Prefer_repeatable_revenue_over_one_off_work",
        "Prefer_fast_evidence_over_speculation",
        "Diversify_sources",
        "Never_count_interest_as_revenue",
        "Never_bypass_platform_rules_or_legal_requirements",
        "Never_move_or_spend_funds_without_explicit_authorization",
    ],
    "strategies": STRATEGIES,
    "recommended_next": STRATEGIES[0]["id"],
    "commercial_state_machine": [
        "MONETIZATION_PATH_DEFINED",
        "CUSTOMER_VALIDATED",
        "PAYMENT_PENDING",
        "PAYMENT_VERIFIED",
        "REVENUE_REALIZED",
        "PROFIT_VERIFIED",
    ],
}

ROOT.mkdir(exist_ok=True)
(ROOT / "revenue_strategy.json").write_text(
    json.dumps(policy, ensure_ascii=False, indent=2) + "\n"
)

print(json.dumps({
    "recommended_next": policy["recommended_next"],
    "top_strategies": [
        (s["id"], s["strategy_score"]) for s in STRATEGIES[:3]
    ],
    "payment_gate": policy["commercial_truth"],
    "financial_authority": policy["financial_authority"],
}, ensure_ascii=False, indent=2))
