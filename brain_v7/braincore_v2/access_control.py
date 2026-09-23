"""API key authentication and scope enforcement for Brain V7.

Keys are supplied only through the runtime environment. Plaintext keys are
never stored or returned. Deployments may use BRAIN_API_KEY or the JSON map
BRAIN_API_KEYS={"admin":"...","code":"..."}.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessIdentity:
    key_id: str
    scopes: frozenset[str]


class AccessController:
    """Bearer-key gate with explicit scopes and independent write switches."""

    def __init__(self) -> None:
        self.enabled = os.getenv("BRAIN_API_AUTH", "true").lower() not in {"0", "false", "no"}
        self.write_enabled = os.getenv("BRAIN_CODE_WRITE_ENABLED", "false").lower() in {"1", "true", "yes"}
        self.publish_enabled = os.getenv("BRAIN_CODE_GITHUB_PUBLISH_ENABLED", "false").lower() in {"1", "true", "yes"}
        self._keys = self._load_keys()
        self.default_scopes = frozenset(
            x.strip() for x in os.getenv(
                "BRAIN_API_SCOPES",
                "brain:read,code:read,code:preview,code:verify",
            ).split(",") if x.strip()
        )

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _load_keys(self) -> dict[str, str]:
        raw = os.getenv("BRAIN_API_KEYS", "").strip()
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items() if str(v)}
            except (TypeError, ValueError):
                pass
        single = os.getenv("BRAIN_API_KEY", "").strip()
        return {"default": single} if single else {}

    def authenticate(self, token: str | None) -> AccessIdentity | None:
        if not self.enabled:
            return AccessIdentity(
                "disabled-auth",
                frozenset({
                    "brain:read", "code:read", "code:preview", "code:verify",
                    "code:write", "code:checkpoint", "code:restore", "code:publish",
                }),
            )
        if not token:
            return None
        for key_id, expected in self._keys.items():
            if hmac.compare_digest(token, expected):
                return AccessIdentity(key_id, self._scopes_for(key_id))
        return None

    def _scopes_for(self, key_id: str) -> frozenset[str]:
        raw = os.getenv(f"BRAIN_API_SCOPES_{key_id.upper().replace('-', '_')}", "")
        if raw:
            return frozenset(x.strip() for x in raw.split(",") if x.strip())
        return self.default_scopes

    def allowed(self, identity: AccessIdentity | None, scope: str) -> bool:
        return identity is not None and scope in identity.scopes

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "configured_keys": len(self._keys),
            "write_enabled": self.write_enabled,
            "github_publish_enabled": self.publish_enabled,
            "secret_exposed": False,
            "key_values_returned": False,
        }
