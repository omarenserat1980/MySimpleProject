import os
import hashlib
import time
from typing import Iterable


class SecretControlPlane:
    """Single source of truth for secret metadata/control.

    It never returns secret values. Remote provider credentials are only
    checked for presence/fingerprint; creation or rotation must happen in
    the provider's own credential system.
    """

    REQUIRED = (
        {
            "name": "BRAIN_INDUSTRIAL_CLIENT_KEY_SHA256",
            "scope": ("industrial_clients",),
            "purpose": "SHA-256 verification material for bounded industrial-client authentication",
            "provider_action": "attach_generated_client_hash",
        },
        {
            "name": "OPENAI_API_KEY",
            "scope": ("web",),
            "purpose": "OpenAI API access for the V12 AI gateway",
            "provider_action": "create_or_attach",
        },
        {
            "name": "BRAIN_CONTROL_KEY",
            "scope": ("control_plane",),
            "purpose": "Brain control-plane authentication",
            "provider_action": "generate_or_attach_internal",
        },
        {
            "name": "CLOUDFLARE_API_TOKEN",
            "scope": ("cloudflare",),
            "purpose": "Cloudflare Worker/D1/R2 deployment",
            "provider_action": "attach_provider_credential",
        },
        {
            "name": "CLOUDFLARE_ACCOUNT_ID",
            "scope": ("cloudflare",),
            "purpose": "Cloudflare account targeting",
            "provider_action": "attach_provider_identifier",
        },
        {
            "name": "PAYTABS_SERVER_KEY",
            "scope": ("payments",),
            "purpose": "PayTabs server-side payment requests",
            "provider_action": "attach_provider_credential",
        },
        {
            "name": "PAYTABS_PROFILE_ID",
            "scope": ("payments",),
            "purpose": "PayTabs payment profile",
            "provider_action": "attach_provider_identifier",
        },
    )

    def __init__(self, environment=None):
        self.environment = environment if environment is not None else os.environ

    @staticmethod
    def _configured(value):
        return bool(str(value or "").strip())

    @staticmethod
    def _fingerprint(value):
        if not value:
            return None
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]

    def status(self):
        items = []
        for spec in self.REQUIRED:
            value = self.environment.get(spec["name"])
            items.append({
                "name": spec["name"],
                "configured": self._configured(value),
                "fingerprint": self._fingerprint(value),
                "scope": list(spec["scope"]),
                "purpose": spec["purpose"],
                "provider_action": spec["provider_action"],
                "value_exposed": False,
            })
        return {
            "ok": True,
            "provider": "environment_secret_store",
            "secrets": items,
            "missing": [x["name"] for x in items if not x["configured"]],
            "policy": "NEVER_RETURN_SECRET_VALUES",
            "checked_at": time.time(),
        }

    def plan(self, names: Iterable[str] | None = None):
        requested = set(names or [x["name"] for x in self.REQUIRED])
        specs = [x for x in self.REQUIRED if x["name"] in requested]
        known = {x["name"] for x in self.REQUIRED}
        unknown = sorted(requested - known)
        return {
            "ok": not unknown,
            "status": "READY" if not unknown else "UNKNOWN_SECRET",
            "provider": "external_secret_connector_required_for_remote_write",
            "secrets": [
                {
                    "name": x["name"],
                    "scope": list(x["scope"]),
                    "purpose": x["purpose"],
                    "action": x["provider_action"],
                    "write_requires_explicit_approval": True,
                    "value_returned": False,
                }
                for x in specs
            ],
            "unknown": unknown,
        }
