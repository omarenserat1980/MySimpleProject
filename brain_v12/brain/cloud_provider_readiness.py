"""Fail-closed discovery of configured cloud-provider adapters.

This module does not contact providers or provision resources. Environment-variable
presence is only a hint that a credential may be configured; it is not proof that
the credential works, that an account is authorized, or that compute is free.
"""
from __future__ import annotations

import os
from typing import Mapping


_PROVIDER_REQUIREMENTS = {
    "azure": ("AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"),
    "aws": ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"),
    "gcp": ("GOOGLE_APPLICATION_CREDENTIALS",),
}


def discover_provider_configuration(environment: Mapping[str, str] | None = None) -> dict:
    """Return secret-safe provider configuration readiness without provisioning."""
    env = environment if environment is not None else os.environ
    providers = []
    for provider, required in _PROVIDER_REQUIREMENTS.items():
        present = [name for name in required if str(env.get(name, "")).strip()]
        missing = [name for name in required if name not in present]
        configured = not missing
        providers.append({
            "provider": provider,
            "status": "CONFIGURED_UNVERIFIED" if configured else "NOT_CONFIGURED",
            "required_variables": list(required),
            "configured_variables": present,
            "missing_variables": missing,
            "secret_values_exposed": False,
            "authenticated": False,
            "free_capacity_verified": False,
            "provisioning_allowed": False,
        })

    configured_count = sum(p["status"] == "CONFIGURED_UNVERIFIED" for p in providers)
    return {
        "status": "CONFIGURATION_CANDIDATES_FOUND" if configured_count else "NO_AUTHORIZED_PROVIDER",
        "providers": providers,
        "configured_provider_count": configured_count,
        "provider_api_checked": False,
        "zero_cost_verified": False,
        "physical_node_verified": False,
        "provisioning_allowed": False,
        "next_step": (
            "Run a provider-specific read-only identity, entitlement, quota, region, SKU, "
            "and complete-cost preflight; require explicit owner approval before provisioning."
            if configured_count
            else "Connect an owner-authorized provider credential through the runtime secret store; "
                 "do not paste or commit secrets."
        ),
    }
