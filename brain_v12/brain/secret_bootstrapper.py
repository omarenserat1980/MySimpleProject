"""Generate and validate internal Brain secrets without exposing their values."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import MutableMapping


DEFAULT_SECRET_BYTES = 32


@dataclass(frozen=True)
class SecretGeneration:
    name: str
    created: bool
    fingerprint: str


def _fingerprint(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


class SecretBootstrapper:
    """Bootstrap internal secrets in an injected secret store.

    This class never prints, returns, or logs secret values. External provider
    credentials (Cloudflare/PayTabs) are intentionally not generated here.
    """

    def __init__(self, store: MutableMapping[str, str] | None = None):
        self.store = store if store is not None else {}

    def ensure(self, names: list[str]) -> list[SecretGeneration]:
        results: list[SecretGeneration] = []
        for name in names:
            if not name or not name.replace("_", "").isalnum():
                raise ValueError(f"invalid secret name: {name!r}")
            existing = self.store.get(name)
            if existing:
                results.append(
                    SecretGeneration(name=name, created=False, fingerprint=_fingerprint(existing))
                )
                continue
            value = secrets.token_urlsafe(DEFAULT_SECRET_BYTES)
            self.store[name] = value
            results.append(
                SecretGeneration(name=name, created=True, fingerprint=_fingerprint(value))
            )
        return results
