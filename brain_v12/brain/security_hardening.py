"""Defensive runtime hardening primitives.

Provider-neutral and fail-closed. No exploit tooling is included.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
import re
import time
from collections import defaultdict


SENSITIVE_NAME_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|"
    r"access[_-]?key|authorization|cookie|set-cookie|iban|card|cvv)",
    re.I,
)
SECRET_VALUE_RE = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"AKIA[A-Z0-9]{16}|Bearer\s+[A-Za-z0-9._-]{16,})"
)


@dataclass(frozen=True)
class SecurityConfig:
    require_control_key: bool = True
    rate_limit_per_minute: int = 60
    max_body_bytes: int = 8 * 1024 * 1024


class SecurityHardener:
    def __init__(self, config: SecurityConfig | None = None):
        self.config = config or SecurityConfig()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def validate_control_key(self, supplied: str | None) -> bool:
        expected = os.getenv("BRAIN_CONTROL_KEY", "")
        if not expected or not supplied:
            return False
        return hmac.compare_digest(supplied, expected)

    def allow_rate(self, identity: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        window = now - 60.0
        hits = [t for t in self._hits[identity] if t > window]
        self._hits[identity] = hits
        if len(hits) >= self.config.rate_limit_per_minute:
            return False
        hits.append(now)
        return True

    @staticmethod
    def security_headers() -> dict[str, str]:
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            "Cache-Control": "no-store",
        }

    @staticmethod
    def redact_mapping(data: dict) -> dict:
        out = {}
        for key, value in data.items():
            if SENSITIVE_NAME_RE.search(str(key)):
                out[key] = "[REDACTED]"
            elif isinstance(value, str) and SECRET_VALUE_RE.search(value):
                out[key] = "[REDACTED]"
            else:
                out[key] = value
        return out

    @staticmethod
    def fingerprint_public(data: object) -> str:
        raw = repr(data).encode("utf-8", "replace")
        return hashlib.sha256(raw).hexdigest()[:24]
