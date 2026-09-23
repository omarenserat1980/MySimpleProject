"""Evidence checklist for regulated financial workflows."""
from __future__ import annotations
CHECKS=("identity_verified","destination_verified","source_of_funds_recorded",
        "transaction_purpose_recorded","provider_confirmed","audit_recorded")
def evaluate(record:dict)->dict:
    missing=[x for x in CHECKS if not record.get(x,False)]
    return {"compliant":not missing,"missing":missing,
            "status":"READY" if not missing else "REVIEW_REQUIRED"}
