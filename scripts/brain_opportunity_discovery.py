import json
from pathlib import Path
from datetime import datetime, timezone

SOURCES = [
    {"id":"open_source_bounties","family":"FREE_DIVERSE","value":8,"success":0.35,"evidence":0.9,"risk":1,"cost":0,"complexity":3},
    {"id":"brain_games","family":"BRAIN_OWNED","value":9,"success":0.20,"evidence":0.8,"risk":2,"cost":0,"complexity":5},
    {"id":"digital_tools","family":"BRAIN_OWNED","value":8,"success":0.25,"evidence":0.85,"risk":1,"cost":0,"complexity":4},
    {"id":"micro_saas","family":"BRAIN_OWNED","value":10,"success":0.15,"evidence":0.8,"risk":2,"cost":0,"complexity":6},
    {"id":"github_sponsors","family":"FREE_DIVERSE","value":7,"success":0.12,"evidence":0.95,"risk":1,"cost":0,"complexity":2},
    {"id":"ai_demos_free_compute","family":"FREE_DIVERSE","value":7,"success":0.18,"evidence":0.8,"risk":2,"cost":0,"complexity":4},
]

def score(x):
    return round((x["value"] * x["success"] * x["evidence"]) / max(1, x["risk"] + x["cost"] + x["complexity"]), 6)

for x in SOURCES:
    x["score"] = score(x)
SOURCES.sort(key=lambda x: x["score"], reverse=True)

state = {
    "schema":"brain.opportunity_queue.v1",
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "commercial_truth":"DISCOVERY_ONLY_UNTIL_PAYMENT_VERIFIED",
    "autonomy_order":["BRAIN_OWNED","FREE_DIVERSE","PAID_EXTERNAL"],
    "candidates":SOURCES,
    "selected_next":SOURCES[0]["id"],
    "gates":{
        "legal":True,
        "financial_side_effects_blocked":True,
        "payment_verification_required":True,
        "paid_external_disabled_by_default":True
    }
}
Path(".brain_state").mkdir(exist_ok=True)
Path(".brain_state/opportunity_queue.json").write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(state,ensure_ascii=False,indent=2))
