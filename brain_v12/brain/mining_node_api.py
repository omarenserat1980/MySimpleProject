"""Evidence-first API for the Brain Mining Node.

This module reports integration/readiness state only. It does not start mining,
contact a pool, allocate cloud resources, or treat caller-supplied claims as proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from .brain_owned_mining_contract import build_plan, execution_gate
from .brain_owned_compute_runtime import double_sha256, execution_host_gate
from .compute_resource_manager import build_compute_resource_report
from .braiins_pool_evidence_collector import BRAIINS_WORKERS_URL
from .control_auth import require_control_key
from ..business.mining_activity_ledger import MiningActivityLedger

router = APIRouter(prefix="/api/mining-node", tags=["Brain Mining Node"])

NODE_MODE = "SIMULATOR"
INTEGRATED_COMPONENTS = (
    "brain_supervisor",
    "asic_simulator",
    "bitcoin_mining_intelligence",
    "brain_owned_mining_contract",
    "brain_owned_sha256d_pow_primitive",
    "brain_owned_compute_backend_pending",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_real_mining_evidence(evidence: Any) -> dict[str, Any]:
    """Fail-closed classification; untrusted JSON cannot establish real mining.

    A real claim needs server-collected, independently verifiable evidence. This
    API intentionally has no endpoint that accepts evidence and promotes state.
    """
    if not isinstance(evidence, dict):
        evidence = {}
    required = (
        "authenticated_host_attestation",
        "authenticated_brain_connection",
        "pool_session_attestation",
        "accepted_share_attestation",
    )
    missing = [key for key in required if not isinstance(evidence.get(key), dict)
               or evidence[key].get("verified") is not True
               or not evidence[key].get("source")
               or not evidence[key].get("digest")]
    return {
        "real_mining_verified": False,
        "state": "BLOCKED" if missing else "REQUIRES_INDEPENDENT_SERVER_VERIFICATION",
        "missing_evidence": missing,
        "note": "Submitted fields are claims, not proof; only trusted server-side collectors may verify them.",
    }


def node_status() -> dict[str, Any]:
    return {
        "ok": True,
        "node_id": "brain-mining-node-local",
        "node_mode": NODE_MODE,
        "state": "SIMULATED",
        "execution_mode": "BRAIN_OWNED_SOFTWARE_ONLY_PLAN_ONLY",
        "physical_devices_role": "CONNECTIVITY_OBSERVATION_ONLY",
        "native_pow_primitive": "IMPLEMENTED_SHA256D_BOUNDED",
        "bounded_nonce_search_available": True,
        "production_compute_service_implemented": False,
        "execution_gate_state": "BLOCKED",
        "native_mining_backend": "NOT_IMPLEMENTED",
        "bounded_software_compute_primitive": "AVAILABLE_SHA256D_LIBRARY",
        "compute_preflight_endpoint": "/api/mining-node/compute-preflight",
        "pool_evidence_status_endpoint": "/api/mining-node/pool-evidence/status",
        "live_compute_ready": False,
        "external_miner_execution": "FORBIDDEN",
        "local_device_computation_allowed": False,
        "integrated_components": list(INTEGRATED_COMPONENTS),
        "real_mining_claim": False,
        "revenue_claim": False,
        "network_access_performed": False,
        "hardware_access_performed": False,
        "timestamp_utc": utc_now(),
    }


def readiness_status() -> dict[str, Any]:
    return {
        "ok": True,
        "node_mode": NODE_MODE,
        "software_api_ready": True,
        "real_mining_ready": False,
        "execution_allowed": False,
        "execution_started": False,
        "state": "BLOCKED",
        "execution_mode": "BRAIN_OWNED_SOFTWARE_ONLY_PLAN_ONLY",
        "physical_devices_role": "CONNECTIVITY_OBSERVATION_ONLY",
        "native_pow_primitive": "IMPLEMENTED_SHA256D_BOUNDED",
        "native_mining_backend": "NOT_IMPLEMENTED",
        "gates": {
            "G0_api_contract": "READY",
            "G1_simulation": "READY",
            "G1a_sha256d_pow_primitive": "READY_BOUNDED_LIBRARY_ONLY",
            "G2_brain_owned_compute_backend": "BLOCKED_LIVE_BACKEND_NOT_IMPLEMENTED",
            "G2a_bounded_sha256d_primitive": "READY_BOUNDED_LIBRARY_ONLY",
            "G2a1_bounded_nonce_search": "AVAILABLE_LIBRARY_ONLY",
            "G2b_live_compute_host_attestation": "BLOCKED_HOST_ATTESTATION_REQUIRED",
            "G2b1_live_compute_service": "BLOCKED_NOT_EXPOSED",
            "G2c_pool_share_submission_adapter": "BLOCKED_NOT_IMPLEMENTED",
            "G3_brain_runtime_attestation": "NOT_VERIFIED_BY_THIS_API",
            "G4_gateway_connectivity": "NOT_REQUIRED_FOR_COMPUTE",
            "G5_pool_shares": "BLOCKED_NO_VERIFIED_POOL_SHARES",
            "G6_payout": "BLOCKED_NO_VERIFIED_PAYOUT",
            "G7_profit": "BLOCKED_NO_VERIFIED_COST_AND_REVENUE",
        },
        "blockers": [
            "The SHA256d primitive and bounded nonce-search function exist at library level for offline/bounded use only; the production Brain-owned compute service is not implemented and no live nonce-search endpoint is exposed.",
            "A production Brain compute host has not been independently attested, and live execution remains blocked.",
            "No Stratum share-submission adapter or independently verified pool-session/share evidence is bound to the Brain runtime.",
            "Payout and profit evidence are not available through this API.",
        ],
        "real_mining_claim": False,
        "revenue_claim": False,
        "timestamp_utc": utc_now(),
    }


def compute_backend_preflight() -> dict[str, Any]:
    """Run a fixed SHA256d known-answer test without searching nonces or using the network."""
    expected = (
        "4f8b42c22dd3729b519ba6f68d2da7cc"
        "5b2d606d05daed5ad5128cc03e6c6358"
    )
    actual = double_sha256(b"abc").hex()
    gate = execution_host_gate(
        attested_brain_compute_host=False,
        explicit_approval=False,
        pool_adapter_ready=False,
        resource_budget_verified=False,
        physical_gateway_only=True,
    )
    return {
        "ok": actual == expected,
        "status": "PRIMITIVE_SELF_TEST_PASSED" if actual == expected else "PRIMITIVE_SELF_TEST_FAILED",
        "backend": "BOUNDED_SHA256D_SOFTWARE_LIBRARY",
        "known_answer_test_passed": actual == expected,
        "nonce_search_executed": False,
        "pool_contacted": False,
        "network_access_performed": False,
        "physical_device_computation_allowed": False,
        "live_compute_ready": False,
        "execution_allowed": False,
        "execution_started": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "live_execution_gate": gate,
    }



def compute_resource_status() -> dict[str, Any]:
    """Report local CPU/RAM capacity without starting work or touching networks."""
    report = build_compute_resource_report()
    report["status"] = "READ_ONLY_RESOURCE_INVENTORY_AVAILABLE"
    report["endpoint_execution_performed"] = False
    report["pool_contacted"] = False
    report["share_submitted"] = False
    report["real_mining_verified"] = False
    report["revenue_verified"] = False
    return report


def pool_evidence_status() -> dict[str, Any]:
    """Describe the read-only collector without making a pool request or inspecting credentials."""
    return {
        "ok": True,
        "status": "READ_ONLY_COLLECTOR_AVAILABLE_AWAITING_AUTHORIZED_CONFIGURATION",
        "provider": "Braiins Pool",
        "endpoint": BRAIINS_WORKERS_URL,
        "http_method": "GET",
        "authentication": "Pool-Auth-Token header; token must be supplied via an existing protected environment setting",
        "operator_must_use_read_only_access_profile": True,
        "pool_credential_scope_verified": False,
        "tls_verification_required": True,
        "redirects_allowed": False,
        "pool_settings_changed": False,
        "pool_query_performed": False,
        "network_access_performed": False,
        "pool_activity_verified": False,
        "accepted_share_submission_verified": False,
        "brain_runtime_activity_verified": False,
        "payout_verified": False,
        "revenue_verified": False,
        "execution_allowed": False,
        "note": "Pool API aggregate telemetry is independent of worker self-reports, but does not prove Brain generated the work or verify an individual accepted-share submission.",
    }


@router.get("/simulation-contract")
def get_simulation_contract() -> dict[str, Any]:
    """Backward-compatible offline contract check; never contacts a pool."""
    from .stratum_v1_offline_simulator import OfflineStratumSimulator

    simulator = OfflineStratumSimulator()
    subscribe = simulator.handle({"id": 1, "method": "mining.subscribe", "params": []})
    authorize = simulator.handle({"id": 2, "method": "mining.authorize", "params": ["sim.worker", "offline-placeholder"]})
    submit = simulator.handle({"id": 3, "method": "mining.submit", "params": ["sim.worker", "offline-job", "aabb", "65aa0000", "00000000"]})
    unauthorized = OfflineStratumSimulator().handle({"id": 4, "method": "mining.submit", "params": ["sim.worker", "offline-job", "aabb", "65aa0000", "00000000"]})
    checks = {
        "subscribe_contract": subscribe.get("result") is not None,
        "authorize_contract": authorize.get("result") is True,
        "submit_contract": submit.get("result") is True and simulator.submitted_count == 1,
        "unauthorized_submit_blocked": isinstance(unauthorized.get("error"), dict),
        "all_responses_marked_simulated": all(item.get("simulated") is True for item in (subscribe, authorize, submit, unauthorized)),
        "no_response_claims_pool_acceptance": all(item.get("pool_acceptance_verified") is False for item in (subscribe, authorize, submit, unauthorized)),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "checks_total": len(checks),
        "network_access_performed": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "note": "Offline compatibility contract only; not proof of live pool acceptance.",
    }


def stratum_candidate_pipeline_status() -> dict[str, Any]:
    """Expose pipeline integration capability without executing a job or touching the network."""
    from . import stratum_candidate_pipeline

    available = callable(stratum_candidate_pipeline.prepare_and_search_job) and callable(
        stratum_candidate_pipeline.validate_job_network_target
    )
    return {
        "ok": available,
        "component": "stratum_candidate_pipeline",
        "status": "AVAILABLE_OFFLINE_BOUNDED" if available else "UNAVAILABLE",
        "prepare_and_search_job_available": callable(stratum_candidate_pipeline.prepare_and_search_job),
        "network_target_validation_available": callable(stratum_candidate_pipeline.validate_job_network_target),
        "execution_performed": False,
        "network_access_performed": False,
        "pool_contacted": False,
        "share_submitted": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "evidence_class": "OFFLINE_BOUNDED_POW_CANDIDATE_ONLY",
        "note": "Capability discovery only; this endpoint does not execute nonce search or infer live pool activity.",
    }


@router.get("/stratum-pipeline/status")
def get_stratum_candidate_pipeline_status() -> dict[str, Any]:
    return stratum_candidate_pipeline_status()


@router.post("/activity")
def record_mining_activity(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist mining activity without requiring payout proof; control-key protected."""
    require_control_key(request)
    ledger = MiningActivityLedger()
    try:
        return ledger.record(**payload)
    finally:
        ledger.close()


@router.get("/activity/{activity_id}")
def get_mining_activity(request: Request, activity_id: str) -> dict[str, Any]:
    """Retrieve a persisted activity record; never promotes estimates to revenue."""
    require_control_key(request)
    ledger = MiningActivityLedger()
    try:
        record = ledger.get(activity_id)
        if record is None:
            raise HTTPException(status_code=404, detail="mining activity not found")
        return record
    finally:
        ledger.close()


@router.get("/status")
def get_mining_node_status() -> dict[str, Any]:
    """Return truthful node status without activating workers or external services."""
    return node_status()


@router.get("/compute-preflight")
def get_compute_backend_preflight() -> dict[str, Any]:
    return compute_backend_preflight()


@router.get("/compute-resources")
def get_compute_resource_status() -> dict[str, Any]:
    """Expose a read-only host resource inventory; never launches a compute job."""
    return compute_resource_status()


@router.get("/pool-evidence/status")
def get_pool_evidence_status() -> dict[str, Any]:
    return pool_evidence_status()


@router.get("/readiness")
def get_mining_node_readiness() -> dict[str, Any]:
    """Return software readiness separately from real mining readiness."""
    return readiness_status()


@router.get("/software-only-contract")
def get_software_only_contract() -> dict[str, Any]:
    """Expose the canonical software-only plan and fail-closed execution gate."""
    return {
        "plan": build_plan("sha256d"),
        "execution_gate": execution_gate(),
        "execution_allowed": False,
        "execution_started": False,
    }
