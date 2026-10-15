"""Evidence-first API for the Brain Mining Node.

This module reports integration/readiness state only. It does not start mining,
contact a pool, allocate cloud resources, or treat caller-supplied claims as proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/mining-node", tags=["Brain Mining Node"])

NODE_MODE = "SIMULATOR"
INTEGRATED_COMPONENTS = (
    "brain_supervisor",
    "asic_simulator",
    "bitcoin_mining_intelligence",
    "bitcoin_worker",
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
        "gates": {
            "G0_api_contract": "READY",
            "G1_simulation": "READY",
            "G2_sha256d_reference": "NOT_VERIFIED_BY_THIS_API",
            "G3_rtl_tool_evidence": "NOT_VERIFIED_BY_THIS_API",
            "G4_physical_device": "BLOCKED_NO_VERIFIED_DEVICE",
            "G5_pool_shares": "BLOCKED_NO_VERIFIED_POOL_SHARES",
            "G6_payout": "BLOCKED_NO_VERIFIED_PAYOUT",
            "G7_profit": "BLOCKED_NO_VERIFIED_COST_AND_REVENUE",
        },
        "blockers": [
            "No trusted physical-device attestation is connected to this API.",
            "No server-collected authenticated pool session or accepted-share evidence is connected.",
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
