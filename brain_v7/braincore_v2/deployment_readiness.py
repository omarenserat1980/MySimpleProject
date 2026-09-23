"""Machine-readable production and deployment checklist.

The checklist is designed to be used by CI or a deployment operator. It never
turns a configured environment variable into proof that an external service is
reachable.
"""
from __future__ import annotations

from typing import Any


REQUIRED_RUNTIME_ENV = (
    "BRAIN_SLEEP_SECONDS",
    "FACTORY_INTERVAL_SECONDS",
)


def inspect_environment(env: dict[str, str]) -> dict[str, Any]:
    present = {key: bool(str(env.get(key, "")).strip()) for key in REQUIRED_RUNTIME_ENV}
    return {
        "required_runtime": present,
        "runtime_configured": all(present.values()),
        "external_secrets_detected": False,
        "note": "Provider credentials must remain in the deployment secret store.",
    }


def inspect_factory_config(env: dict[str, str]) -> dict[str, Any]:
    production = str(env.get("FACTORY_ALLOW_PRODUCTION", "0")).lower() in {"1", "true", "yes", "on"}
    publication = str(env.get("FACTORY_ALLOW_YOUTUBE_PUBLISH", "0")).lower() in {"1", "true", "yes", "on"}
    return {
        "production_authorized": production,
        "youtube_publish_authorized": publication,
        "authorization_is_not_proof_of_success": True,
    }
