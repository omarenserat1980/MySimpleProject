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

now = datetime.now(timezone.utc).isoformat()
selected = SOURCES[0]
task_id = "OPP-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

queue = {
    "schema":"brain.opportunity_queue.v2",
    "generated_at":now,
    "commercial_truth":"DISCOVERY_ONLY_UNTIL_PAYMENT_VERIFIED",
    "autonomy_order":["BRAIN_OWNED","FREE_DIVERSE","PAID_EXTERNAL"],
    "candidates":SOURCES,
    "selected_next":selected["id"],
    "selected_task":{
        "task_id":task_id,
        "opportunity_id":selected["id"],
        "state":"READY_FOR_EXECUTION",
        "required_evidence":["scope","execution_result","verification_result"],
        "commercial_state":"MONETIZATION_PATH_DEFINED",
        "payment_state":"NOT_VERIFIED"
    },
    "gates":{
        "legal":True,
        "financial_side_effects_blocked":True,
        "payment_verification_required":True,
        "paid_external_disabled_by_default":True
    }
}

root=Path(".brain_state")
root.mkdir(exist_ok=True)
(root/"opportunity_queue.json").write_text(json.dumps(queue,ensure_ascii=False,indent=2)+"\n")
(root/"opportunity_task.json").write_text(json.dumps(queue["selected_task"],ensure_ascii=False,indent=2)+"\n")
print(json.dumps(queue,ensure_ascii=False,indent=2))
