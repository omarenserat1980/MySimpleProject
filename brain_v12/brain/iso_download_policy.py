"""Fail-closed source and integrity policy helpers for ISO downloads.

This module performs no network request. Callers must revalidate every redirect and
pin validated DNS addresses to the actual connection; a separate DNS lookup alone
does not prevent DNS rebinding.
"""
from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlsplit

from .iso_download_store import DownloadError


def allowed_hosts_from_env(value: str | None = None) -> frozenset[str]:
    raw = os.getenv("BRAIN_ISO_ALLOWED_HOSTS", "") if value is None else value
    hosts = set()
    for item in raw.split(","):
        host = item.strip().lower().rstrip(".")
        if not host:
            continue
        if "/" in host or ":" in host or "*" in host or "@" in host:
            raise DownloadError("INVALID_SOURCE_POLICY")
        hosts.add(host)
    return frozenset(hosts)


def validate_source_url(url: str, *, allowed_hosts: frozenset[str] | set[str],
                        resolve_dns: bool = True) -> dict:
    """Allow exact HTTPS hosts only; reject credentials, unusual ports and private IPs."""
    if not isinstance(url, str) or len(url) > 4096:
        raise DownloadError("SOURCE_NOT_ALLOWED")
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        port = parts.port
    except ValueError as exc:
        raise DownloadError("SOURCE_NOT_ALLOWED") from exc
    if (parts.scheme.lower() != "https" or not host or parts.username or parts.password
            or parts.fragment or port not in (None, 443) or host not in allowed_hosts):
        raise DownloadError("SOURCE_NOT_ALLOWED")
    addresses: set[str] = set()
    try:
        literal = ipaddress.ip_address(host)
        addresses.add(str(literal))
    except ValueError:
        if resolve_dns:
            try:
                answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            except OSError as exc:
                raise DownloadError("SOURCE_DNS_FAILED") from exc
            addresses.update(answer[4][0] for answer in answers)
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address.split("%", 1)[0])
        except ValueError as exc:
            raise DownloadError("SOURCE_NOT_ALLOWED") from exc
        if not parsed.is_global:
            raise DownloadError("SOURCE_NOT_ALLOWED")
    if resolve_dns and not addresses:
        raise DownloadError("SOURCE_DNS_FAILED")
    return {"scheme": "https", "host": host, "port": 443,
            "resolved_addresses": sorted(addresses)}


def verify_file_integrity(path: str | os.PathLike[str], *,
                          expected_size: int | None,
                          expected_sha256: str | None) -> dict:
    """Verify a regular non-symlink file against a trusted SHA-256 and optional size."""
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise DownloadError("INTEGRITY_CHECK_FAILED")
    if (expected_sha256 is None or len(expected_sha256) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in expected_sha256)):
        raise DownloadError("INTEGRITY_METADATA_REQUIRED")
    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise DownloadError("INTEGRITY_CHECK_FAILED") from exc
    actual = digest.hexdigest()
    if (expected_size is not None and size != expected_size) or actual.lower() != expected_sha256.lower():
        raise DownloadError("INTEGRITY_CHECK_FAILED")
    return {"verified": True, "size_bytes": size, "sha256": actual}
