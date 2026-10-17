"""Brain Mining Controller.

Safe planning and policy evaluation for a future Brain-owned mining backend.
Hardware discovery and miner compatibility are advisory only: this module does
not launch a miner, contact a pool, or establish that mining is profitable.

Actual execution remains blocked until a native Brain-owned backend is
implemented, attested, and separately reviewed. GitHub Actions never mines.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import platform
import shutil
from typing import Any


@dataclass(frozen=True)
class MiningPolicy:
    enabled: bool = False
    max_cpu_percent: float = 50.0
    max_runtime_minutes: int = 60
    max_temperature_c: float = 75.0
    require_profitability: bool = True
    require_user_owned_worker: bool = True
    allow_github_actions: bool = False


@dataclass(frozen=True)
class HardwareProfile:
    os: str
    arch: str
    cpu_count: int
    ram_gb: float
    miners_present: tuple[str, ...]


@dataclass(frozen=True)
class MiningPlan:
    algorithm: str
    miner: str
    backend: str
    mode: str
    reason: str
    execution_mode: str = "PLAN_ONLY"
    external_miner_execution_allowed: bool = False


MINER_REGISTRY = {
    "randomx": ("xmrig", "cpu"),
    "kawpow": ("xmrig", "cpu/gpu"),
    "cryptonight": ("xmrig", "cpu/gpu"),
    "ghostrider": ("xmrig", "cpu/gpu"),
}


def _ram_gb() -> float:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * page_size / (1024 ** 3), 2)
    except (AttributeError, OSError, ValueError):
        return 0.0


def detect_hardware() -> HardwareProfile:
    present = tuple(
        name for name in ("xmrig", "cpuminer", "lolMiner", "t-rex")
        if shutil.which(name)
    )
    return HardwareProfile(
        os=platform.system().lower(),
        arch=platform.machine().lower(),
        cpu_count=os.cpu_count() or 1,
        ram_gb=_ram_gb(),
        miners_present=present,
    )


def choose_plan(
    hardware: HardwareProfile,
    algorithm: str = "randomx",
    require_installed_miner: bool = False,
) -> MiningPlan:
    """Return compatibility advice only; never authorize or start a miner."""
    algorithm = algorithm.lower()
    if algorithm not in MINER_REGISTRY:
        raise ValueError(f"unsupported algorithm: {algorithm}")

    miner, backend = MINER_REGISTRY[algorithm]
    installed = miner in hardware.miners_present
    if require_installed_miner and not installed:
        raise RuntimeError(f"{miner} is not installed on this worker")

    mode = "fast" if hardware.ram_gb >= 3.0 else "light"
    return MiningPlan(
        algorithm=algorithm,
        miner=miner,
        backend=backend,
        mode=mode,
        reason=(
            "compatibility recommendation only; external miner execution is "
            "blocked and the Brain-owned native backend is pending"
        ),
        execution_mode="PLAN_ONLY",
        external_miner_execution_allowed=False,
    )


def profitability_gate(
    gross_revenue_per_hour: float,
    electricity_cost_per_hour: float,
    pool_fee_per_hour: float = 0.0,
    hardware_cost_per_hour: float = 0.0,
    minimum_margin: float = 0.0,
) -> dict[str, Any]:
    net = gross_revenue_per_hour - electricity_cost_per_hour - pool_fee_per_hour - hardware_cost_per_hour
    margin = (net / gross_revenue_per_hour) if gross_revenue_per_hour > 0 else -1.0
    return {
        "gross_revenue_per_hour": gross_revenue_per_hour,
        "cost_per_hour": electricity_cost_per_hour + pool_fee_per_hour + hardware_cost_per_hour,
        "net_per_hour": round(net, 8),
        "margin": round(margin, 6),
        "profitable": net > minimum_margin,
    }


def can_start(
    policy: MiningPolicy,
    *,
    worker_is_user_owned: bool,
    running_on_github_actions: bool,
    current_temperature_c: float | None = None,
    brain_owned_backend_implemented: bool = False,
    backend_attested: bool = False,
    pool_endpoint_verified: bool = False,
    credentials_in_secret_store: bool = False,
    resource_budget_verified: bool = False,
    explicit_user_approval: bool = False,
) -> tuple[bool, str]:
    """Fail closed; this policy check never launches a process or contacts a pool."""
    if running_on_github_actions:
        return False, "github_actions_mining_forbidden"
    if policy.require_user_owned_worker and not worker_is_user_owned:
        return False, "worker_not_registered_as_user_owned"
    if not policy.enabled:
        return False, "mining_disabled_by_default"
    if current_temperature_c is not None and current_temperature_c >= policy.max_temperature_c:
        return False, "thermal_limit_reached"
    if not brain_owned_backend_implemented:
        return False, "brain_owned_mining_backend_not_implemented"
    if not backend_attested:
        return False, "brain_backend_attestation_required"
    if not pool_endpoint_verified:
        return False, "pool_endpoint_verification_required"
    if not credentials_in_secret_store:
        return False, "pool_credentials_secret_store_required"
    if not resource_budget_verified:
        return False, "resource_budget_verification_required"
    if not explicit_user_approval:
        return False, "explicit_user_approval_required"
    return False, "separate_execution_review_required"


def evidence_record(
    *,
    worker_id: str,
    algorithm: str,
    runtime_seconds: int,
    hashrate: float,
    accepted_shares: int,
    rejected_shares: int,
    payout_tx_id: str | None = None,
    verified_received: float = 0.0,
    currency: str = "XMR",
) -> dict[str, Any]:
    """Return auditable evidence; verified_received must come from payment proof."""
    return {
        "worker_id": worker_id,
        "algorithm": algorithm,
        "runtime_seconds": runtime_seconds,
        "hashrate": hashrate,
        "accepted_shares": accepted_shares,
        "rejected_shares": rejected_shares,
        "payout_tx_id": payout_tx_id,
        "verified_received": verified_received,
        "currency": currency,
        "status": "VERIFIED_RECEIVED" if verified_received > 0 and payout_tx_id else "MINING_EVIDENCE_ONLY",
    }


def status() -> dict[str, Any]:
    return {
        "controller": "Brain Mining Controller",
        "policy": asdict(MiningPolicy()),
        "hardware": asdict(detect_hardware()),
        "github_actions_mining": "BLOCKED",
        "default_mode": "PLAN_ONLY",
        "external_miner_execution": "BLOCKED",
        "brain_owned_backend": "PENDING_IMPLEMENTATION_AND_REVIEW",
    }


if __name__ == "__main__":
    print(json.dumps(status(), indent=2, sort_keys=True))
