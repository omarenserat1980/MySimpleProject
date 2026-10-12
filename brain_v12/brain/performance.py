from __future__ import annotations

"""Small, fail-closed performance primitives for Brain runtime hot paths.

The cache is intentionally short-lived and only caches *successful* substrate
preflight results. Authority, contracts, leadership/fencing, and guest evidence
must never be cached here.
"""

from dataclasses import dataclass
import os
import time
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    expires_at: float


class ShortTTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float = 2.0) -> None:
        if ttl_seconds <= 0:
            raise ValueError("TTL_MUST_BE_POSITIVE")
        self.ttl_seconds = float(ttl_seconds)
        self._entries: dict[str, _Entry[T]] = {}

    def get_or_compute(self, key: str, compute: Callable[[], T], *, cacheable: Callable[[T], bool] | None = None) -> T:
        now = time.monotonic()
        entry = self._entries.get(key)
        if entry and entry.expires_at > now:
            return entry.value
        value = compute()
        if cacheable is None or cacheable(value):
            self._entries[key] = _Entry(value=value, expires_at=now + self.ttl_seconds)
        return value

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._entries.clear()
        else:
            self._entries.pop(key, None)


def performance_cache_ttl() -> float:
    raw = os.environ.get("BRAIN_PREFLIGHT_CACHE_TTL_SECONDS", "2")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError("BRAIN_PREFLIGHT_CACHE_TTL_INVALID") from exc
    if value <= 0 or value > 10:
        raise RuntimeError("BRAIN_PREFLIGHT_CACHE_TTL_OUT_OF_RANGE")
    return value
