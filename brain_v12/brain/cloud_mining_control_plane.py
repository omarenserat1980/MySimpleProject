"""Brain-owned software-only mining control plane.

Physical devices are connectivity/observation gateways only. This module can
plan work for a Brain-owned software node, but it cannot dispatch mining or
admit real execution until a native Brain-owned backend is implemented.
Telemetry and payout references remain untrusted until independently verified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any


@dataclass(frozen=True)
class CloudWorker:
    worker_id: str
    kind: str
    region: str
    owner: str
    enabled: bool = False
    max_temperature_c: float = 75.0
    max_cpu_percent: float = 50.0


@dataclass(frozen=True)
class MiningJob:
    job_id: str
    worker_id: str
    algorithm: str
    miner: str
    mode: str
    status: str = "PLANNED"


ALLOWED_SOFTWARE_NODE_KINDS = {"vm", "software_node", "brain_vm", "container"}
FORBIDDEN_PHYSICAL_KINDS = {
    "physical", "device", "android", "termux", "phone", "desktop", "laptop",
    "asic", "gpu", "cpu", "hardware", "redmi3", "realme",
}


class CloudMiningControlPlane:
    def __init__(self) -> None:
        self.workers: dict[str, CloudWorker] = {}
        self.jobs: dict[str, MiningJob] = {}

    def register_worker(self, worker: CloudWorker) -> None:
        if not worker.worker_id.strip() or not worker.owner.strip():
            raise ValueError("worker identity and owner are required")
        kind = str(worker.kind).strip().lower()
        if kind in FORBIDDEN_PHYSICAL_KINDS or kind not in ALLOWED_SOFTWARE_NODE_KINDS:
            raise ValueError(
                "mining worker must be a Brain-owned software node; physical devices are gateways only"
            )
        if (
            isinstance(worker.max_temperature_c, bool)
            or not isinstance(worker.max_temperature_c, (int, float))
            or not math.isfinite(worker.max_temperature_c)
            or not 0 < worker.max_temperature_c <= 120
        ):
            raise ValueError("max_temperature_c must be finite and in (0, 120]")
        if (
            isinstance(worker.max_cpu_percent, bool)
            or not isinstance(worker.max_cpu_percent, (int, float))
            or not math.isfinite(worker.max_cpu_percent)
            or not 0 < worker.max_cpu_percent <= 100
        ):
            raise ValueError("max_cpu_percent must be finite and in (0, 100]")
        self.workers[worker.worker_id] = worker

    def plan(self, worker_id: str, algorithm: str = "randomx") -> MiningJob:
        worker = self.workers.get(worker_id)
        if worker is None:
            raise KeyError("unknown worker")
        if not worker.enabled:
            raise PermissionError("worker is disabled")
        if algorithm != "randomx":
            raise ValueError("cloud planner currently supports randomx")
        job_id = hashlib.sha256(
            f"{worker_id}:{algorithm}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        job = MiningJob(
            job_id,
            worker_id,
            algorithm,
            "brain-native-backend-pending",
            "plan-only",
            status="BLOCKED_BACKEND_NOT_IMPLEMENTED",
        )
        self.jobs[job_id] = job
        return job

    def admit(
        self,
        job_id: str,
        *,
        on_github_actions: bool = False,
        temperature_c: float | None = None,
        cpu_percent: float | None = None,
    ) -> tuple[bool, str]:
        job = self.jobs.get(job_id)
        if job is None:
            return False, "unknown_job"
        if on_github_actions:
            return False, "github_actions_mining_forbidden"
        worker = self.workers[job.worker_id]
        if not worker.enabled:
            return False, "worker_disabled"
        if temperature_c is not None:
            if (
                isinstance(temperature_c, bool)
                or not isinstance(temperature_c, (int, float))
                or not math.isfinite(temperature_c)
            ):
                return False, "invalid_temperature_telemetry"
            if temperature_c >= worker.max_temperature_c:
                return False, "thermal_limit_reached"
        if cpu_percent is not None:
            if (
                isinstance(cpu_percent, bool)
                or not isinstance(cpu_percent, (int, float))
                or not math.isfinite(cpu_percent)
                or not 0 <= cpu_percent <= 100
            ):
                return False, "invalid_cpu_telemetry"
            if cpu_percent > worker.max_cpu_percent:
                return False, "cpu_limit_reached"
        # A registered software node is not proof that Brain has a native
        # mining backend. Never dispatch to an external miner as a fallback.
        return False, "brain_owned_mining_backend_not_implemented"

    def evidence(
        self,
        job_id: str,
        hashrate: float,
        accepted: int,
        rejected: int,
        payout_tx_id: str | None = None,
    ) -> dict[str, Any]:
        """Record reported telemetry without promoting it to verified mining or revenue."""
        if job_id not in self.jobs:
            raise KeyError("unknown_job")
        if (
            isinstance(hashrate, bool)
            or not isinstance(hashrate, (int, float))
            or not math.isfinite(hashrate)
            or hashrate < 0
        ):
            raise ValueError("hashrate must be a finite non-negative number")
        for name, value in (("accepted", accepted), ("rejected", rejected)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} shares must be a non-negative integer")
        tx_reference = payout_tx_id.strip() if payout_tx_id is not None else None
        if tx_reference == "":
            raise ValueError("payout_tx_id must be non-empty when provided")
        return {
            "schema": "brain-mining-evidence/v1",
            "job_id": job_id,
            "worker_id": self.jobs[job_id].worker_id,
            "hashrate": hashrate,
            "accepted_shares": accepted,
            "rejected_shares": rejected,
            "payout_tx_id": tx_reference,
            "evidence_source": "caller_supplied_unverified_telemetry",
            "financial_state": "NOT_VERIFIED",
            "status": "PAYOUT_TX_REFERENCE_PRESENT" if tx_reference else "MINING_EVIDENCE_ONLY",
            "payout_verified": False,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "service": "Brain Cloud Mining Control Plane",
            "workers": [asdict(w) for w in self.workers.values()],
            "jobs": [asdict(j) for j in self.jobs.values()],
            "execution": "brain_owned_software_runtime_plan_only",
            "physical_devices_role": "connectivity_observation_only",
            "native_mining_backend": "NOT_IMPLEMENTED",
            "external_miner_execution": "FORBIDDEN",
            "github_actions_mining": "BLOCKED",
            "payout_truth_boundary": "transaction_reference_is_not_chain_verification",
            "revenue_realization": "requires_independent_blockchain_proof",
        }


if __name__ == "__main__":
    print(json.dumps(CloudMiningControlPlane().snapshot(), indent=2))
