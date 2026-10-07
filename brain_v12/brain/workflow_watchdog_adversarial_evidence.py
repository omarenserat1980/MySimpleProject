import json
from pathlib import Path

from brain_v12.brain.workflow_watchdog_policy import partition_failures, recovery_allowed

target_sha = "a" * 40
old_sha = "b" * 40
rows = [
    {"run_id": 91001, "head_sha": target_sha},
    {"run_id": 91002, "head_sha": old_sha},
    {"run_id": 91003},
]
eligible, ignored = partition_failures(rows, target_sha)
evidence = {
    "contract": "TARGET_HEAD_SHA_ONLY",
    "cross_sha_recovery": "DENY",
    "target_sha": target_sha,
    "eligible_run_ids": [r["run_id"] for r in eligible],
    "ignored_run_ids": [r["run_id"] for r in ignored],
    "recovery_allowed": {
        str(r["run_id"]): recovery_allowed(r, target_sha) for r in rows
    },
}
assert evidence["eligible_run_ids"] == [91001], evidence
assert evidence["ignored_run_ids"] == [91002, 91003], evidence
assert evidence["recovery_allowed"]["91001"] is True, evidence
assert evidence["recovery_allowed"]["91002"] is False, evidence
assert evidence["recovery_allowed"]["91003"] is False, evidence
out = Path("brain6_artifacts/workflow_watchdog_adversarial")
out.mkdir(parents=True, exist_ok=True)
(out / "adversarial-policy-evidence.json").write_text(
    json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
)
print("CROSS_SHA_POLICY=VERIFIED")
print("TARGET_RECOVERY=ALLOWED")
print("CROSS_SHA_RECOVERY=DENIED")
print("MISSING_SHA_RECOVERY=DENIED")
