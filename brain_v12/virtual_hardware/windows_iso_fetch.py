from __future__ import annotations

"""Fetch official Windows Server ISO media onto the remote VM executor.

The phone never needs to store the ISO. The executor downloads to its own
cache, supports byte-range resume when the server allows it, and refuses to
accept media without an expected SHA-256 supplied by the operator.
"""

import hashlib
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_ALLOWED_SUFFIX = ".microsoft.com"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_CHUNK_SIZE = 8 * 1024 * 1024


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host or not (
        host == "microsoft.com" or host.endswith(_ALLOWED_SUFFIX)
    ):
        raise ValueError("WINDOWS_ISO_URL_MUST_BE_HTTPS_MICROSOFT")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("WINDOWS_ISO_URL_AUTH_OR_PORT_NOT_ALLOWED")


class _MicrosoftRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_official_windows_iso(
    url: str,
    destination: str | Path,
    *,
    expected_sha256: str,
    timeout: int = 60,
) -> dict[str, object]:
    """Download/resume the ISO on the executor host and verify its SHA-256.

    URL values (which may contain temporary signed tokens) are never returned
    in result data or exception messages. Only HTTPS Microsoft hosts are
    allowed, including redirects. The final file is atomically promoted after
    hash verification; an incomplete .part file is retained for resumption.
    """
    _validate_url(url)
    if not _SHA256_RE.fullmatch(expected_sha256 or ""):
        raise ValueError("WINDOWS_ISO_EXPECTED_SHA256_REQUIRED")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0

    request_headers = {"User-Agent": "ElectronicBrain-WindowsMedia/1.0",
                       "Accept-Encoding": "identity"}
    if offset:
        request_headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(url, headers=request_headers)
    opener = urllib.request.build_opener(_MicrosoftRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            if offset and status == 206:
                content_range = response.headers.get("Content-Range", "")
                match = re.match(r"bytes (\d+)-(\d+)/(\d+|\*)$", content_range)
                if not match or int(match.group(1)) != offset:
                    raise RuntimeError("WINDOWS_ISO_RANGE_RESPONSE_INVALID")
                mode = "ab"
            elif status == 200:
                offset = 0
                mode = "wb"
            else:
                raise RuntimeError("WINDOWS_ISO_HTTP_STATUS_INVALID")
            with partial.open(mode) as output:
                while True:
                    block = response.read(_CHUNK_SIZE)
                    if not block:
                        break
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
    except urllib.error.URLError as exc:
        # Do not include the request URL: it may carry an expiring signature.
        raise RuntimeError("WINDOWS_ISO_DOWNLOAD_FAILED") from exc

    digest = hashlib.sha256()
    size = 0
    with partial.open("rb") as source:
        while True:
            block = source.read(_CHUNK_SIZE)
            if not block:
                break
            size += len(block)
            digest.update(block)
    actual_sha256 = digest.hexdigest()
    if actual_sha256.lower() != expected_sha256.lower():
        raise RuntimeError("WINDOWS_ISO_SHA256_MISMATCH")
    if size == 0:
        raise RuntimeError("WINDOWS_ISO_EMPTY")
    partial.replace(target)
    return {
        "ok": True,
        "status": "WINDOWS_ISO_DOWNLOADED_AND_VERIFIED",
        "path": str(target),
        "size_bytes": size,
        "sha256": actual_sha256,
        "resumed": offset > 0,
        "source_policy": "https-microsoft-hosts-only",
    }
