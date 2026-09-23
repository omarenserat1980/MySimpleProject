"""Classify opportunities the brain can execute without external submission.

The brain may autonomously create local deliverables and verification evidence.
External publication, bidding, account actions, contracts, and payments remain
permissioned side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable


@dataclass(frozen=True)
class SelfExecutableOpportunity:
    name: str
    service: str
    input_required: str
    output_artifact: str
    estimated_hours: float
    can_execute_locally: bool = True
    external_submission_required: bool = True
    payment_required: bool = True


BUILTIN = (
    SelfExecutableOpportunity(
        "Arabic product copy package", "product_copy",
        "product facts/photos", "ready-to-publish Arabic copy", 0.25
    ),
    SelfExecutableOpportunity(
        "Short product promo", "short_video",
        "product facts/photos", "rendered short video", 1.0
    ),
    SelfExecutableOpportunity(
        "Product ad creative", "ad_creative",
        "product photo/facts", "finished ad creative", 0.5
    ),
    SelfExecutableOpportunity(
        "Product listing package", "listing_package",
        "product facts/photos", "title + description + specs + CTA", 0.5
    ),
    SelfExecutableOpportunity(
        "Content repurposing pack", "content_repurpose",
        "one source article/video", "multiple short posts/scripts", 0.5
    ),
    SelfExecutableOpportunity(
        "Data cleaning/report", "data_processing",
        "user-provided dataset", "cleaned dataset + report", 0.5
    ),
)


def catalog() -> list[dict[str, Any]]:
    return [asdict(x) for x in BUILTIN]


def classify(
    *,
    can_create_artifact: bool,
    has_required_input: bool,
    external_submission_authorized: bool = False,
) -> dict[str, Any]:
    if not can_create_artifact or not has_required_input:
        return {
            "status": "NOT_READY",
            "self_executable": False,
            "reason": "MISSING_EXECUTION_CAPABILITY_OR_INPUT",
        }
    return {
        "status": "SELF_EXECUTABLE",
        "self_executable": True,
        "artifact_can_be_created": True,
        "external_submission_authorized": bool(external_submission_authorized),
        "payment_verified": False,
        "income_claim_allowed": False,
    }


def select_autonomous_work(items: Iterable[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Select work whose deliverable can be produced locally.

    This intentionally does not imply that the work is paid or that a client
    has accepted it.
    """
    rows = list(items) if items is not None else catalog()
    return [
        x for x in rows
        if bool(x.get("can_execute_locally", True))
        and str(x.get("input_required", "")).strip()
    ]
