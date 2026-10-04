"""Commercial release gate. Never equates CI success with a saleable film."""
from __future__ import annotations
def evaluate(project,qc,rights,review):
    errors=[]
    if qc.get("status")!="PASS": errors.append("qc_failed")
    if not rights.get("complete"): errors.append("rights_evidence_incomplete")
    if not review.get("story_complete"): errors.append("story_review_incomplete")
    if not review.get("sound_complete"): errors.append("sound_review_incomplete")
    if not review.get("continuity_complete"): errors.append("continuity_review_incomplete")
    return {"status":"VERIFIED_COMMERCIAL" if not errors else "BLOCKED","errors":errors}
