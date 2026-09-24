import os
import hashlib
import time
from typing import Iterable


class SecretControlPlane:
    """Secret metadata/control plane.

    It never returns secret values. It reports only configuration state and
    provides a safe plan for an external secret provider/connector.
    """

    REQUIRED = (
        {
            "name": "RENDER_API_KEY",
            "scope": ("web", "render-monitor-worker"),
            "purpose": "Render API read access for deployment/log supervision",
            "provider_action": "create_or_attach",
        },
        {
            "name": "RENDER_OWNER_ID",
            "scope": ("web", "render-monitor-worker"),
            "purpose": "Render account owner identifier",
            "provider_action": "set",
        },
        {
            "name": "OPENAI_API_KEY",
            "scope": ("web",),
            "purpose": "OpenAI API access for the V12 AI gateway",
            "provider_action": "create_or_attach",
        },
    )

    def __init__(self, environment=None):
        self.environment = environment or os.environ

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
        unknown = sorted(requested - {x["name"] for x in self.REQUIRED})
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
