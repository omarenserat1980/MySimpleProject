"""Canonical software-only mining execution contract for Electronic Brain.

Physical devices are connectivity/observation gateways only. Mining computation
must run in a Brain-owned software execution environment. This module is policy
and evidence classification only: it does not launch miners, contact pools, or
claim that a native compute backend exists.
"""
from __future__ import annotations

from typing import Any

SUPPORTED_ALGORITHMS = {"sha256d", "randomx", "kawpow", "cryptonight", "ghostrider"}
EXECUTION_TARGET = "brain_owned_software_runtime"
GATEWAY_ROLE = "connectivity_observation_only"


def build_plan(algorithm: str, *, gateway_id: str | None = None) -> dict[str, Any]:
    """Build a plan without assigning computation to a physical gateway."""
    normalized = str(algorithm or "").strip().lower()
    if normalized not in SUPPORTED_ALGORITHMS:
        raise ValueError("UNSUPPORTED_ALGORITHM")
    normalized_gateway = str(gateway_id or "").strip() or None
    if normalized_gateway and (
        len(normalized_gateway) > 128 or any(ord(char) < 32 for char in normalized_gateway)
    ):
        raise ValueError("INVALID_GATEWAY_ID")
    return {
        "ok": True,
        "status": "PLAN_ONLY_BRAIN_BACKEND_PENDING",
        "algorithm": normalized,
        "execution_target": EXECUTION_TARGET,
        "backend_implemented": False,
        "gateway": {
            "id": normalized_gateway,
            "role": GATEWAY_ROLE,
            "may_compute": False,
            "may_forward_connectivity": True,
            "may_supply_read_only_observations": True,
        },
        "physical_device_computation_allowed": False,
        "external_miner_execution_allowed": False,
        "github_actions_mining_allowed": False,
        "execution_started": False,
        "pool_contacted": False,
        "real_hashrate_hs": None,
        "real_accepted_shares": None,
        "simulation_counts_as_real_mining": False,
        "blocker": "BRAIN_OWNED_MINING_COMPUTE_BACKEND_NOT_IMPLEMENTED",
    }


def execution_gate(
    *,
    backend_implemented: bool = False,
    backend_attested: bool = False,
    pool_endpoint_verified: bool = False,
    credentials_in_secret_store: bool = False,
    resource_budget_verified: bool = False,
    explicit_user_approval: bool = False,
    running_on_github_actions: bool = False,
) -> dict[str, Any]:
    """Evaluate prerequisites; never starts execution or authorizes a stub backend."""
    blockers: list[str] = []
    if not backend_implemented:
        blockers.append("BRAIN_OWNED_BACKEND_NOT_IMPLEMENTED")
    if not backend_attested:
        blockers.append("BRAIN_BACKEND_ATTESTATION_REQUIRED")
    if not pool_endpoint_verified:
        blockers.append("POOL_ENDPOINT_VERIFICATION_REQUIRED")
    if not credentials_in_secret_store:
        blockers.append("POOL_CREDENTIAL_SECRET_STORE_REQUIRED")
    if not resource_budget_verified:
        blockers.append("RESOURCE_BUDGET_VERIFICATION_REQUIRED")
    if not explicit_user_approval:
        blockers.append("EXPLICIT_USER_APPROVAL_REQUIRED")
    if running_on_github_actions:
        blockers.append("GITHUB_ACTIONS_MINING_FORBIDDEN")
    prerequisites_satisfied = not blockers
    return {
        # `ok` means gate evaluation completed without declared blockers; it does
        # not mean execution is authorized. Keep the distinction explicit.
        "ok": prerequisites_satisfied,
        "prerequisites_satisfied": prerequisites_satisfied,
        "status": "BLOCKED" if blockers else "READY_FOR_SEPARATE_EXECUTION_REVIEW",
        "execution_review_required": prerequisites_satisfied,
        "blockers": blockers,
        "execution_allowed": False,
        "execution_started": False,
        "physical_device_computation_allowed": False,
        "external_miner_execution_allowed": False,
        "pool_contacted": False,
        "secrets_read": False,
        "settings_changed": False,
    }


def classify_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Require independent pool evidence and Brain-runtime provenance."""
    if not isinstance(evidence, dict):
        raise ValueError("INVALID_EVIDENCE")
    if evidence.get("simulation") is True or str(evidence.get("evidence_class", "")).startswith("SIMULATION"):
        return {"status": "SIMULATION_ONLY", "counts_as_real_mining": False, "revenue_verified": False}
    try:
        hashrate = float(evidence.get("hashrate_hs", 0))
        accepted = int(evidence.get("accepted_shares", 0))
    except (TypeError, ValueError):
        return {"status": "INVALID_EVIDENCE_FIELDS", "counts_as_real_mining": False, "revenue_verified": False}
    if hashrate <= 0 or accepted <= 0:
        return {"status": "NO_PROOF_OF_ACTIVE_MINING", "counts_as_real_mining": False, "revenue_verified": False}
    valid_provenance = (
        str(evidence.get("source", "")).lower() == "pool_api"
        and bool(str(evidence.get("worker_id", "")).strip())
        and evidence.get("pool_source_verified") is True
        and evidence.get("brain_runtime_attested") is True
        and evidence.get("compute_host") == EXECUTION_TARGET
        and evidence.get("physical_device_computation") is False
        and evidence.get("external_miner_execution") is False
    )
    if not valid_provenance:
        return {
            "status": "UNVERIFIED_OR_ARCHITECTURE_VIOLATING_EVIDENCE",
            "counts_as_real_mining": False,
            "revenue_verified": False,
        }
    return {
        "status": "BRAIN_RUNTIME_POOL_ACTIVITY_VERIFIED",
        "counts_as_real_mining": True,
        "revenue_verified": False,
        "worker_id": str(evidence["worker_id"]),
        "hashrate_hs": hashrate,
        "accepted_shares": accepted,
        "note": "Pool activity evidence does not by itself prove payout or profit.",
    }
