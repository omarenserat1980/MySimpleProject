"""Single source of truth for whether a Brain film may be sold."""
REQUIRED=("master_sha256","qc","rights","story_review","sound_review","continuity_review")
def evaluate(manifest):
    missing=[x for x in REQUIRED if not manifest.get(x)]
    if manifest.get("status")!="VERIFIED_COMMERCIAL": missing.append("verified_commercial_status")
    return {"sellable":not missing,"status":"VERIFIED_COMMERCIAL" if not missing else "BLOCKED","missing":missing}
