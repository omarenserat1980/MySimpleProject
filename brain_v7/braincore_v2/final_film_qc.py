"""Final assembly QC for a production, independent of provider."""
from __future__ import annotations
from typing import Any

def evaluate_final_film(manifest:dict[str,Any], outputs:list[dict[str,Any]])->dict[str,Any]:
    expected=[s.get("shot_id") for s in manifest.get("shots",[])]
    actual=[o.get("shot_id") for o in outputs if o.get("status")=="VERIFIED_COMPLETED"]
    missing=[x for x in expected if x not in actual]
    duplicates=sorted({x for x in actual if actual.count(x)>1})
    ordered=actual==expected
    checks={"all_shots_verified":not missing,"no_duplicates":not duplicates,"shot_order":ordered,
            "manifest_present":bool(manifest),"outputs_present":bool(outputs)}
    status="VERIFIED" if all(checks.values()) else "REPAIR"
    return {"status":status,"checks":checks,"missing":missing,"duplicates":duplicates,"actual_count":len(actual),"expected_count":len(expected)}
