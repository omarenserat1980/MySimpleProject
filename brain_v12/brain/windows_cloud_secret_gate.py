"""Fail-closed readiness gate for Windows Cloud guest enrollment.

This module checks configuration presence only. Secret values are never returned,
logged, fingerprinted, or included in the readiness response.
"""

import os
from typing import Mapping


def _present(value) -> bool:
    return bool(str(value or "").strip())


def _first_present(env: Mapping[str, str], names: tuple[str, ...]):
    for name in names:
        if _present(env.get(name)):
            return name
    return None


def check_windows_cloud_secret_readiness(environment=None):
    env = environment if environment is not None else os.environ

    control_name = _first_present(env, ("BRAIN_CONTROL_TOKEN", "BRAIN_CONTROL_KEY"))
    checks = [
        {
            "name": "fabric_url",
            "configured": _present(env.get("BRAIN_FABRIC_URL")),
            "required": True,
            "secret": False,
        },
        {
            "name": "windows_node_id",
            "configured": _present(env.get("BRAIN_WINDOWS_NODE_ID")),
            "required": True,
            "secret": False,
        },
        {
            "name": "enrollment_token",
            "configured": _present(env.get("BRAIN_ENROLLMENT_TOKEN")),
            "required": True,
            "secret": True,
        },
        {
            "name": "control_auth",
            "configured": control_name is not None,
            "required": True,
            "secret": True,
            "source": control_name,
        },
    ]

    missing = [x["name"] for x in checks if x["required"] and not x["configured"]]
    ready = not missing

    return {
        "ok": ready,
        "status": "READY" if ready else "NOT_READY",
        "capability": "windows-server-2025-cloud-guest-enrollment",
        "checks": [
            {
                "name": x["name"],
                "configured": x["configured"],
                "required": x["required"],
                "secret": x["secret"],
                **({"source": x["source"]} if x["name"] == "control_auth" and x["configured"] else {}),
                "value_exposed": False,
            }
            for x in checks
        ],
        "missing": missing,
        "policy": "PRESENCE_ONLY_NEVER_RETURN_SECRET_VALUES",
        "provisioning_note": "Cloud provider provisioning remains a separate capability and requires an installed provider adapter.",
    }
