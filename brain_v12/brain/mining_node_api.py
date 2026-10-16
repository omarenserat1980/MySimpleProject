"""Evidence-first API for the Brain Mining Node.

This module reports integration/readiness state only. It does not start mining,
contact a pool, allocate cloud resources, or treat caller-supplied claims as proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from .brain_owned_mining_contract import build_plan, execution_gate

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
        "native_mining_backend": "NOT_IMPLEMENTED",
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
        "state": "BLOCKED",
        "execution_mode": "BRAIN_OWNED_SOFTWARE_ONLY_PLAN_ONLY",
        "physical_devices_role": "CONNECTIVITY_OBSERVATION_ONLY",
        "native_pow_primitive": "IMPLEMENTED_SHA256D_BOUNDED",
        "native_mining_backend": "NOT_IMPLEMENTED",
        "gates": {
            "G0_api_contract": "READY",
            "G1_simulation": "READY",
            "G1a_sha256d_pow_primitive": "READY_BOUNDED_LIBRARY_ONLY",
            "G2_brain_owned_compute_backend": "BLOCKED_NOT_IMPLEMENTED",
            "G3_brain_runtime_attestation": "NOT_VERIFIED_BY_THIS_API",
            "G4_gateway_connectivity": "NOT_REQUIRED_FOR_COMPUTE",
            "G5_pool_shares": "BLOCKED_NO_VERIFIED_POOL_SHARES",
            "G6_payout": "BLOCKED_NO_VERIFIED_PAYOUT",
            "G7_profit": "BLOCKED_NO_VERIFIED_COST_AND_REVENUE",
        },
        "blockers": [
            "The bounded SHA256d proof-of-work primitive is a library only; the Brain-owned native mining compute backend is not implemented.",
            "No independently verified pool session or accepted-share evidence is bound to a Brain runtime.",
            "Payout and profit evidence are not available through this API.",
        ],
        "real_mining_claim": False,
        "revenue_claim": False,
        "timestamp_utc": utc_now(),
    }


@router.get("/status")
def get_mining_node_status() -> dict[str, Any]:
    """Return truthful node status without activating workers or external services."""
    return node_status()


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
