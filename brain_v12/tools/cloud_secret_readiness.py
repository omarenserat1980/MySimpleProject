"""Presence-only readiness check for Brain cloud deployment secrets.

This tool intentionally never prints or validates secret values and never writes secrets.
"""
from __future__ import annotations

import json
import os
from typing import Iterable

DEFAULT_REQUIRED = (
    "CHECK_AZURE_CLIENT_ID",
    "CHECK_AZURE_TENANT_ID",
    "CHECK_AZURE_SUBSCRIPTION_ID",
    "CHECK_WINDOWS_ADMIN_USERNAME",
    "CHECK_WINDOWS_ADMIN_PASSWORD",
)


def inspect_presence(required: Iterable[str] = DEFAULT_REQUIRED, environ=None) -> dict:
    env = os.environ if environ is None else environ
    items = []
    missing = []
    for name in required:
        present = bool(str(env.get(name, "")).strip())
        items.append({"name": name, "present": present})
        if not present:
            missing.append(name)
    return {
        "schema_version": 1,
        "status": "READY" if not missing else "BLOCKED_CONFIGURATION",
        "ready": not missing,
        "required_count": len(items),
        "present_count": len(items) - len(missing),
        "missing_names": missing,
        "checks": items,
        "values_emitted": False,
        "validity_verified": False,
        "next_action": None if not missing else "Configure the missing protected secrets through an authorized secret-write path, then rerun this check.",
    }


if __name__ == "__main__":
    print(json.dumps(inspect_presence(), ensure_ascii=False, indent=2))
