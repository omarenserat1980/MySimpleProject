"""Stable source identity for economic opportunities."""

from __future__ import annotations

from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit


def normalize_source_url(url: str) -> str:
    value = url.strip()
    if not value:
        raise ValueError("source URL cannot be empty")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("source URL must be an absolute http/https URL")

    host = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, parts.query, ""))


def source_fingerprint(url: str) -> str:
    normalized = normalize_source_url(url)
    return sha256(normalized.encode("utf-8")).hexdigest()


def same_source(first: str, second: str) -> bool:
    return source_fingerprint(first) == source_fingerprint(second)
