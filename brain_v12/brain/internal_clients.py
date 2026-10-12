"""Unified internal Brain-client launch path.

Software tools inside Brain address work through this gateway instead of
calling executors/workflows directly. The gateway resolves the active customer
scope, probes the existing backend, builds the bounded staged plan, and fails
closed when the backend is not ready.

This module does not create workflows or perform external side effects.
"""
from __future__ import annotations

from typing import Any

from .windows_cloud_provider_factory import windows_cloud_provider_readiness
from ..business.customer_execution_router import CustomerExecutionRouter
from ..business.two_customer_execution_contract import CUSTOMER_SCOPE, public_scope
from .client_revenue_guardian import GUARDIAN_CLIENT_ID, TARGET_CLIENT_ID
from .executor_identity import configured_executor, identity


INTERNAL_CLIENTS = {
    "BRAIN-INTERNAL-CL-000001": {
        "customer_id": "CL-000001",
        "tool_role": "INDUSTRIAL_ISO_CLIENT",
        "request": "LOAD_AND_BOOT_BRAIN_ISO",
        "target": configured_executor()["executor_id"],
    },
    "BRAIN-INTERNAL-CL-000002": {
        "customer_id": "CL-000002",
        "tool_role": "CLOUD_WINDOWS_SERVER_2025_CLIENT",
        "request": "PROVISION_AND_PREPARE_WINDOWS_SERVER_2025",
        "target": "brain-cloud",
    },
    GUARDIAN_CLIENT_ID: {
        "customer_id": TARGET_CLIENT_ID,
        "tool_role": "REVENUE_ACTIVITY_GUARDIAN",
        "request": "MONITOR_AND_ACCELERATE_VERIFIED_REVENUE",
        "target": TARGET_CLIENT_ID,
        "supervisory_only": True,
    },
}


def _device_bridge_probe(device_bridge: Any) -> dict[str, Any]:
    status = device_bridge.status()
    return {
        "ready": bool(status.get("enabled") and status.get("online")),
        "backend": "DEVICE_BRIDGE",
        "status": status,
    }


def _cloud_probe() -> dict[str, Any]:
    readiness = windows_cloud_provider_readiness()
    return {
        "ready": bool(readiness.get("ready")),
        "backend": "CLOUD_WINDOWS_RUNTIME",
        "status": readiness,
    }


def build_gateway(device_bridge: Any) -> CustomerExecutionRouter:
    return CustomerExecutionRouter({
        "DEVICE_BRIDGE": lambda: _device_bridge_probe(device_bridge),
        "CLOUD_WINDOWS_RUNTIME": _cloud_probe,
    })


def resolve_internal_client(client_id: str) -> dict[str, Any]:
    item = INTERNAL_CLIENTS.get(str(client_id).strip())
    if item is None:
        return {"ok": False, "status": "UNKNOWN_INTERNAL_CLIENT"}
    customer_id = item["customer_id"]
    if item.get("supervisory_only"):
        return {
            "ok": True,
            "client_id": client_id,
            "customer_id": customer_id,
            **item,
            "objective": "مراقبة نشاط CL-000003 والإيراد الفعلي المثبت ودفع مسار محدود نحو الإيراد",
            "backend": "REVENUE_GUARDIAN",
        }
    scope = CUSTOMER_SCOPE[customer_id]
    return {
        "ok": True,
        "client_id": client_id,
        "customer_id": customer_id,
        **item,
        "activity_id": scope["activity_id"],
        "objective": scope["objective"],
        "backend": scope["backend"],
    }


def launch_plan(client_id: str, device_bridge: Any) -> dict[str, Any]:
    client = resolve_internal_client(client_id)
    if not client["ok"]:
        return client
    if client.get("supervisory_only"):
        return {
            "ok": True,
            "status": "SUPERVISORY_READY",
            "client": client,
            "plan": {
                "target_client_id": TARGET_CLIENT_ID,
                "stages": [
                    "INSPECT_ACTIVITY",
                    "INSPECT_VERIFIED_REVENUE",
                    "DIAGNOSE_BLOCKER",
                    "NUDGE_ONE_BOUNDED_ACTION",
                    "VERIFY",
                    "EVIDENCE",
                ],
                "dispatch_allowed": False,
                "completion_allowed": False,
            },
            "execution_policy": "SUPERVISORY_ONLY_EXISTING_PRIMARY_PIPELINE",
            "completion_policy": "VERIFY_AND_EVIDENCE_REQUIRED",
            "recovery": {
                "durable_request_state": True,
                "resume_from_checkpoint": True,
                "reconcile_existing_run_before_dispatch": True,
            },
        }
    router = build_gateway(device_bridge)
    plan = router.build_plan(client["customer_id"])
    return {
        "ok": bool(plan["dispatch_allowed"]),
        "status": "READY_TO_LAUNCH" if plan["dispatch_allowed"] else "LAUNCH_BLOCKED",
        "client": client,
        "plan": plan,
        "execution_policy": "EXISTING_PRIMARY_PIPELINE",
        "completion_policy": "VERIFY_AND_EVIDENCE_REQUIRED",
        "recovery": {
            "durable_request_state": True,
            "resume_from_checkpoint": True,
            "reconcile_existing_run_before_dispatch": True,
        },
    }


def public_registry() -> dict[str, Any]:
    return {
        "ok": True,
        "mode": "BRAIN_INTERNAL_CLIENTS",
        "customer_scope": public_scope(),
        "executor_identity": identity(),
        "clients": [
            {
                "client_id": client_id,
                **{k: v for k, v in item.items()},
            }
            for client_id, item in INTERNAL_CLIENTS.items()
        ],
        "rules": {
            "one_active_request_per_client": True,
            "existing_primary_pipeline_only": True,
            "completion_requires_verification_and_evidence": True,
            "new_workflow_creation": False,
        },
    }
