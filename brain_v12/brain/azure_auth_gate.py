"""Fail-closed Azure authentication readiness for the Brain Windows Cloud runtime.

This module never authenticates, provisions, logs, or returns credential values.
It only reports whether an Azure runtime authentication mechanism is configured.
"""

import os
from typing import Mapping


AZURE_AUTH_ENV = (
    "ARM_CLIENT_ID",
    "ARM_TENANT_ID",
    "ARM_SUBSCRIPTION_ID",
    "ARM_CLIENT_SECRET",
)


def check_azure_auth_readiness(environment: Mapping[str, str] | None = None) -> dict[str, object]:
    env = environment if environment is not None else os.environ
    configured = {name: bool(str(env.get(name, "")).strip()) for name in AZURE_AUTH_ENV}
    missing = [name for name, present in configured.items() if not present]

    return {
        "ok": not missing,
        "status": "READY" if not missing else "NOT_READY",
        "provider": "azure",
        "mechanism": "service_principal_env",
        "checks": [
            {
                "name": name,
                "configured": present,
                "secret": name == "ARM_CLIENT_SECRET",
                "value_exposed": False,
            }
            for name, present in configured.items()
        ],
        "missing": missing,
        "policy": "PRESENCE_ONLY_NEVER_RETURN_SECRET_VALUES",
    }
