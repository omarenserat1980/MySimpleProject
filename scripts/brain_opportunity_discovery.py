import json
import os
import re
import urllib.parse
import urllib.request
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
    return round((x["value"] * x["success"] * x["evidence"]) /
                 max(1, x["risk"] + x["cost"] + x["complexity"]), 6)

def fetch_live_bounties(limit=10):
    query = urllib.parse.quote("bounty is:open")
    url = f"https://api.github.com/search/issues?q={query}&sort=updated&order=desc&per_page={limit}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Brain-Opportunity-Discovery",
    })
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.load(response)
    except Exception as exc:
        return {"status":"UNAVAILABLE", "reason": str(exc), "items":[]}

    items = []
    positive = re.compile(r"\b(code|coding|bug|fix|test|tests|documentation|docs|feature|implementation|analysis)\b", re.I)
    negative = re.compile(r"\b(star|retweet|follow|like|social post|wallet|crypto|token|referral)\b", re.I)
    for issue in data.get("items", []):
        title = issue.get("title", "")
        body = issue.get("body") or ""
        text = f"{title}\n{body}"
        if positive.search(text) and not negative.search(text):
            items.append({
                "source":"github",
                "repository": (issue.get("repository_url") or "").split("/repos/")[-1],
                "issue_number": issue.get("number"),
                "title": title,
                "url": issue.get("html_url"),
                "updated_at": issue.get("updated_at"),
                "evidence_quality": 0.9,
                "payment_claim_requires_verification": True,
            })
    return {"status":"OK", "items":items}

for x in SOURCES:
    x["score"] = score(x)
SOURCES.sort(key=lambda x: x["score"], reverse=True)

live = fetch_live_bounties()
now = datetime.now(timezone.utc).isoformat()
selected = SOURCES[0]
task_id = "OPP-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

selected_target = None
if selected["id"] == "open_source_bounties" and live["items"]:
    selected_target = live["items"][0]

queue = {
    "schema":"brain.opportunity_queue.v3",
    "generated_at":now,
    "commercial_truth":"DISCOVERY_ONLY_UNTIL_PAYMENT_VERIFIED",
    "autonomy_order":["BRAIN_OWNED","FREE_DIVERSE","PAID_EXTERNAL"],
    "candidates":SOURCES,
    "live_sources":{
        "github_bounty_search":live,
    },
    "selected_next":selected["id"],
    "selected_target":selected_target,
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
        "paid_external_disabled_by_default":True,
        "external_submission_requires_authorization":True
    }
}

root=Path(".brain_state")
root.mkdir(exist_ok=True)
(root/"opportunity_queue.json").write_text(json.dumps(queue,ensure_ascii=False,indent=2)+"\n")
(root/"opportunity_task.json").write_text(json.dumps(queue["selected_task"],ensure_ascii=False,indent=2)+"\n")
print(json.dumps(queue,ensure_ascii=False,indent=2))
