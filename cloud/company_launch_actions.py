"""Bounded next-action planner for autonomous company launch."""
from __future__ import annotations


def next_actions(readiness: dict) -> list[dict]:
    status = readiness.get("status")
    blockers = readiness.get("blockers", [])
    actions: list[dict] = []

    if status == "BLOCKED":
        actions.append({
            "action": "REPAIR_RELEASE_GATE",
            "priority": "P0",
            "reason": "Release gate is blocked; repair and re-verify before publication.",
        })
        return actions

    if status == "NEEDS_EVIDENCE":
        for item in blockers:
            if "customer" in item:
                actions.append({
                    "action": "BUILD_CUSTOMER_EVIDENCE",
                    "priority": "P1",
                    "reason": "Identify a concrete customer/demand signal and preserve evidence.",
                })
            if "delivery" in item:
                actions.append({
                    "action": "BUILD_DELIVERY_EVIDENCE",
                    "priority": "P1",
                    "reason": "Produce a verifiable delivery artifact tied to an offer/customer.",
                })
            if "payment_verified" in item:
                actions.append({
                    "action": "VERIFY_PAYMENT_PATH",
                    "priority": "P1",
                    "reason": "Payment must be independently verified before revenue is recognized.",
                })
        if not actions:
            actions.append({
                "action": "RECHECK_EVIDENCE",
                "priority": "P2",
                "reason": "Re-read current evidence and recompute readiness.",
            })
        return actions

    if status == "READY":
        return [{
            "action": "PREPARE_COMMERCIAL_RELEASE",
            "priority": "P1",
            "reason": "Release and commercial evidence gates are satisfied; execute only authorized external steps.",
        }]

    return [{
        "action": "RECHECK_READINESS",
        "priority": "P2",
        "reason": "Unknown readiness state; fail closed and recompute.",
    }]
