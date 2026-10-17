#!/usr/bin/env python3
"""Read-only mining credential/configuration readiness audit.

Reports presence and policy status only. Never prints secret values, loads secret
files, contacts a pool, starts a miner, or changes settings.
"""
from __future__ import annotations

import json
import os
import re
from typing import Mapping

BRAIINS_POOL = (
    "BRAIINS_POOL_API_TOKEN",
    "BRAIINS_POOL_WORKER_ID",
)
BRAIN_WORKER_API = (
    "BRAIN_MINING_WORKER_API_TOKEN",
)
WORKER_CONNECTIVITY = (
    "BRAIN_MINING_API_URL",
    "BRAIN_MINER_STATS_URL",
    "BRAIN_MINING_WORKER_ID",
)
OPTIONAL = ("BRAIN_MINING_HEARTBEAT_SECONDS",)
WORKER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def audit_environment(environ: Mapping[str, str] | None = None) -> dict:
    env = os.environ if environ is None else environ

    def present(name: str) -> bool:
        value = env.get(name, "")
        return isinstance(value, str) and bool(value.strip())

    def domain(names: tuple[str, ...]) -> dict:
        return {
            "required_variables": list(names),
            "variables": {name: {"configured": present(name)} for name in names},
            "ready": all(present(name) for name in names),
        }

    worker_token = env.get("BRAIN_MINING_WORKER_API_TOKEN", "")
    worker_id = env.get("BRAIN_MINING_WORKER_ID", "")
    heartbeat = env.get("BRAIN_MINING_HEARTBEAT_SECONDS", "30").strip()
    try:
        heartbeat_seconds = int(heartbeat)
        heartbeat_policy_ok = 10 <= heartbeat_seconds <= 90
    except (TypeError, ValueError):
        heartbeat_policy_ok = False

    domains = {
        "braiins_readonly_pool_telemetry": domain(BRAIINS_POOL),
        "brain_worker_telemetry_intake": domain(BRAIN_WORKER_API),
        "worker_connectivity": domain(WORKER_CONNECTIVITY),
    }
    # Policy metadata only; never disclose token contents or length.
    domains["brain_worker_telemetry_intake"]["token_policy_satisfied"] = (
        isinstance(worker_token, str) and len(worker_token) >= 32
    )
    domains["worker_connectivity"]["worker_id_format_valid"] = bool(
        isinstance(worker_id, str) and WORKER_ID_PATTERN.fullmatch(worker_id)
    )
    optional_config = {
        name: {"configured": present(name)} for name in OPTIONAL
    }
    optional_config["BRAIN_MINING_HEARTBEAT_SECONDS"]["policy_satisfied"] = heartbeat_policy_ok

    missing = [
        name
        for group in domains.values()
        for name, item in group["variables"].items()
        if not item["configured"]
    ]
    return {
        "schema_version": 1,
        "audit": "brain-mining-configuration-readiness",
        "mode": "READ_ONLY_CONFIGURATION_AUDIT",
        "credential_domains": domains,
        "optional_configuration": optional_config,
        "missing_required_variable_names": sorted(set(missing)),
        "ready_for_braiins_readonly_telemetry": domains["braiins_readonly_pool_telemetry"]["ready"],
        "ready_for_brain_worker_telemetry": (
            domains["brain_worker_telemetry_intake"]["ready"]
            and domains["brain_worker_telemetry_intake"]["token_policy_satisfied"]
            and domains["worker_connectivity"]["ready"]
            and domains["worker_connectivity"]["worker_id_format_valid"]
            and heartbeat_policy_ok
        ),
        "credential_domains_are_not_interchangeable": True,
        "braiins_pool_token_scope_verified": False,
        "worker_reports_are_not_pool_share_proof": True,
        "secret_values_printed": False,
        "secret_files_read": False,
        "network_accessed": False,
        "miner_started": False,
        "pool_settings_changed": False,
        "production_settings_changed": False,
        "real_mining_verified": False,
        "accepted_shares_verified": False,
        "revenue_verified": False,
        "notes": [
            "BRAIINS_POOL_API_TOKEN authenticates the read-only Braiins pool telemetry request.",
            "BRAIN_MINING_WORKER_API_TOKEN authenticates worker telemetry to Brain; it is a different credential.",
            "BRAIN_MINING_API_URL and BRAIN_MINER_STATS_URL are worker connectivity endpoints, not pool credentials.",
            "This audit reports process-environment presence only and does not load .env, .brain_env, or any secret store.",
        ],
    }


def main() -> int:
    print(json.dumps(audit_environment(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
