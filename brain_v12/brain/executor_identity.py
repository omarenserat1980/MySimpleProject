"""Canonical executor identity for Brain's physical execution nodes.

Hostnames are aliases only. Dispatch must use stable executor/device/runner
identifiers so renaming or replacing a host does not change Brain semantics.
"""
from __future__ import annotations

import os
from typing import Any

ARKAN_EXECUTOR_ID = "arkan-executor-01"
ARKAN_RUNNER_ID = "23"
ARKAN_DEVICE_ID = "464fa3dd-e325-435b-8c0e-df0ac46c9f07"
ARKAN_HOST_ALIAS = "arkan"


def configured_executor() -> dict[str, str]:
    return {
        "executor_id": os.getenv("BRAIN_EXECUTOR_ID", ARKAN_EXECUTOR_ID).strip(),
        "runner_id": os.getenv("BRAIN_RUNNER_ID", ARKAN_RUNNER_ID).strip(),
        "device_id": os.getenv("BRAIN_DEVICE_ID", ARKAN_DEVICE_ID).strip(),
        "host_alias": os.getenv("BRAIN_HOST_ALIAS", ARKAN_HOST_ALIAS).strip().lower(),
    }


def matches_agent(agent: dict[str, Any]) -> bool:
    cfg = configured_executor()
    stable = {
        str(agent.get("executor_id") or "").strip(),
        str(agent.get("device_id") or "").strip(),
        str(agent.get("runner_id") or "").strip(),
    }
    if cfg["executor_id"] in stable or cfg["device_id"] in stable or cfg["runner_id"] in stable:
        return True
    # Compatibility only: old agents expose hostname as agent_id.
    return str(agent.get("agent_id") or "").strip().lower() in {
        cfg["host_alias"], "arkan-01", "arkan01", "brain-internal-arkan"
    }


def identity() -> dict[str, Any]:
    cfg = configured_executor()
    return {
        "executor_id": cfg["executor_id"],
        "runner_id": cfg["runner_id"],
        "device_id": cfg["device_id"],
        "host_alias": cfg["host_alias"],
        "identity_policy": "STABLE_IDENTITY_HOSTNAME_ALIAS_ONLY",
    }
