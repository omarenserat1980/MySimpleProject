"""Secure secret broker for Brain runtime and CI.

Secrets are never persisted, logged, or returned.
"""

from __future__ import annotations
import hashlib
import os
from dataclasses import dataclass
from typing import Mapping
from .permissions import PermissionGate

@dataclass(frozen=True)
class SecretStatus:
    name: str
    configured: bool
    fingerprint: str | None = None

class SecretBroker:
    def __init__(self, env: Mapping[str, str] | None = None, gate: PermissionGate | None = None):
        self._env = env if env is not None else os.environ
        self._gate = gate or PermissionGate()

    def _authorize(self, approved: bool = False) -> None:
        result = self._gate.check(["credentials"], approved=approved)
        if not result["allowed"]:
            raise PermissionError("credential capability is not granted")

    def status(self, names: list[str], approved: bool = False) -> list[SecretStatus]:
        self._authorize(approved)
        out = []
        for name in names:
            value = self._env.get(name, "")
            fingerprint = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12] if value else None
            out.append(SecretStatus(name=name, configured=bool(value), fingerprint=fingerprint))
        return out

    def require(self, names: list[str], approved: bool = False) -> None:
        statuses = self.status(names, approved=approved)
        missing = [s.name for s in statuses if not s.configured]
        if missing:
            raise RuntimeError("missing required credentials: " + ", ".join(missing))
