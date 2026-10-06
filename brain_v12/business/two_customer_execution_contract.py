"""Bounded execution contract for the two active Brain customers.

This module is deliberately an execution contract, not an executor. It binds
the current two customer IDs to their intended activities and requires callers
to pass execution through Brain's existing control/verification gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CUSTOMER_SCOPE = {
    "CL-000001": {
        "customer_type": "INDUSTRIAL",
        "activity_id": "ACT-CL-000001-ISO-ARKAN",
        "objective": "تشغيل ISO على جهاز Arkan",
        "backend": "DEVICE_BRIDGE",
    },
    "CL-000002": {
        "customer_type": "CLOUD",
        "activity_id": "ACT-CL-000002-WINDOWS-SERVER-2025",
        "objective": "تحميل/تجهيز Windows Server 2025 سحابياً",
        "backend": "CLOUD_WINDOWS_RUNTIME",
    },
}

TERMINAL = {"VERIFIED_COMPLETED", "CANCELLED", "FAILED"}


@dataclass(frozen=True)
class CustomerActivity:
    customer_id: str
    activity_id: str
    objective: str
    backend: str
    customer_type: str


def resolve_customer(customer_id: str) -> CustomerActivity:
    key = str(customer_id).strip()
    record = CUSTOMER_SCOPE.get(key)
    if record is None:
        raise ValueError("CUSTOMER_OUTSIDE_ACTIVE_SCOPE")
    return CustomerActivity(
        customer_id=key,
        activity_id=record["activity_id"],
        objective=record["objective"],
        backend=record["backend"],
        customer_type=record["customer_type"],
    )


def validate_exact_scope(customer_ids: list[str]) -> tuple[CustomerActivity, CustomerActivity]:
    ids = [str(x).strip() for x in customer_ids]
    if len(ids) != 2 or len(set(ids)) != 2:
        raise ValueError("EXACTLY_TWO_CUSTOMERS_REQUIRED")
    if set(ids) != set(CUSTOMER_SCOPE):
        raise ValueError("ACTIVE_CUSTOMER_SCOPE_MISMATCH")
    return resolve_customer(ids[0]), resolve_customer(ids[1])


def completion_allowed(execution: dict[str, Any]) -> bool:
    """Only objective verification + evidence may authorize completion."""
    if not isinstance(execution, dict):
        return False
    if execution.get("completed") is not True:
        return False
    verification = execution.get("verification")
    if not isinstance(verification, dict):
        return False
    if verification.get("passed") is not True:
        return False
    if not str(verification.get("criterion", "")).strip():
        return False
    evidence = execution.get("evidence")
    return bool(evidence)


def public_scope() -> dict[str, Any]:
    return {
        "customer_count": 2,
        "customer_ids": list(CUSTOMER_SCOPE),
        "exactly_two": True,
        "third_customer_allowed": False,
        "completion_requires": [
            "EXECUTION",
            "OBJECTIVE_VERIFICATION",
            "EVIDENCE",
        ],
        "activities": [
            {
                "customer_id": customer_id,
                "activity_id": value["activity_id"],
                "objective": value["objective"],
                "backend": value["backend"],
            }
            for customer_id, value in CUSTOMER_SCOPE.items()
        ],
    }
