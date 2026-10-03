"""Cloud control plane for Brain's user-owned mining workers.

The cloud coordinates workers; it is not itself a GitHub Actions miner.
Workers must be explicitly registered and owned by the user.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
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


class CloudMiningControlPlane:
    def __init__(self) -> None:
        self.workers: dict[str, CloudWorker] = {}
        self.jobs: dict[str, MiningJob] = {}

    def register_worker(self, worker: CloudWorker) -> None:
        if not worker.worker_id or not worker.owner:
            raise ValueError("worker identity and owner are required")
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
        job = MiningJob(job_id, worker_id, algorithm, "xmrig", "benchmark")
        self.jobs[job_id] = job
        return job

    def admit(self, job_id: str, *, on_github_actions: bool = False,
              temperature_c: float | None = None) -> tuple[bool, str]:
        job = self.jobs.get(job_id)
        if job is None:
            return False, "unknown_job"
        if on_github_actions:
            return False, "github_actions_mining_forbidden"
        worker = self.workers[job.worker_id]
        if temperature_c is not None and temperature_c >= worker.max_temperature_c:
            return False, "thermal_limit_reached"
        return True, "admitted_for_registered_worker"

    def evidence(self, job_id: str, hashrate: float, accepted: int,
                 rejected: int, payout_tx_id: str | None = None) -> dict[str, Any]:
        if job_id not in self.jobs:
            raise KeyError("unknown_job")
        return {
            "job_id": job_id,
            "hashrate": hashrate,
            "accepted_shares": accepted,
            "rejected_shares": rejected,
            "payout_tx_id": payout_tx_id,
            "status": "PAYOUT_TX_REFERENCE_PRESENT" if payout_tx_id else "MINING_EVIDENCE_ONLY",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "service": "Brain Cloud Mining Control Plane",
            "workers": [asdict(w) for w in self.workers.values()],
            "jobs": [asdict(j) for j in self.jobs.values()],
            "execution": "external_registered_worker_only",
            "github_actions_mining": "BLOCKED",
        }


if __name__ == "__main__":
    print(json.dumps(CloudMiningControlPlane().snapshot(), indent=2))
