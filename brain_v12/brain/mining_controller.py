"""Brain Mining Controller.

Safe control-plane for user-owned mining hosts.
It discovers hardware, selects compatible open-source miners, estimates
profitability, and enforces thermal/resource/payout gates.

Important: this module never mines inside GitHub Actions and never moves funds.
Actual mining is opt-in on an explicitly registered external/self-hosted worker.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import platform
import shutil
import subprocess
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
        reason="CPU-first RandomX-compatible plan; actual execution is opt-in",
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
) -> tuple[bool, str]:
    if running_on_github_actions and not policy.allow_github_actions:
        return False, "github_actions_mining_forbidden"
    if policy.require_user_owned_worker and not worker_is_user_owned:
        return False, "worker_not_registered_as_user_owned"
    if not policy.enabled:
        return False, "mining_disabled_by_default"
    if current_temperature_c is not None and current_temperature_c >= policy.max_temperature_c:
        return False, "thermal_limit_reached"
    return True, "approved_by_local_policy"


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
        "default_mode": "BENCHMARK_ONLY",
    }


if __name__ == "__main__":
    print(json.dumps(status(), indent=2, sort_keys=True))
