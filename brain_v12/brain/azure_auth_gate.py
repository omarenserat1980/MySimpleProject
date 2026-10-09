"""Fail-closed Azure authentication readiness for Brain Windows Cloud.

Brain accepts an existing Azure runtime identity without ever creating, printing,
or persisting credentials. Supported mechanisms are service-principal
environment variables, Azure CLI login, and workload/managed identity signals.
Provisioning remains blocked when no identity is available.
"""

import os
import shutil
import subprocess
from typing import Mapping


AZURE_AUTH_ENV = (
    "ARM_CLIENT_ID",
    "ARM_TENANT_ID",
    "ARM_SUBSCRIPTION_ID",
    "ARM_CLIENT_SECRET",
)


def _azure_cli_ready() -> bool:
    az = shutil.which("az")
    if not az:
        return False
    try:
        result = subprocess.run(
            [az, "account", "show", "--only-show-errors"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def check_azure_auth_readiness(
    environment: Mapping[str, str] | None = None,
    *,
    cli_ready: bool | None = None,
) -> dict[str, object]:
    env = environment if environment is not None else os.environ
    configured = {name: bool(str(env.get(name, "")).strip()) for name in AZURE_AUTH_ENV}
    missing = [name for name, present in configured.items() if not present]

    cli = _azure_cli_ready() if cli_ready is None else bool(cli_ready)
    env_ready = not missing
    workload_identity = bool(str(env.get("AZURE_FEDERATED_TOKEN_FILE", "")).strip())
    managed_identity = bool(str(env.get("AZURE_CLIENT_ID", "")).strip())

    mechanisms = []
    if env_ready:
        mechanisms.append("service_principal_env")
    if cli:
        mechanisms.append("azure_cli")
    if workload_identity:
        mechanisms.append("workload_identity")
    if managed_identity:
        mechanisms.append("managed_identity_signal")

    return {
        "ok": bool(mechanisms),
        "status": "READY" if mechanisms else "NOT_READY",
        "provider": "azure",
        "mechanism": mechanisms[0] if mechanisms else None,
        "available_mechanisms": mechanisms,
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
