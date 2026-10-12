#!/usr/bin/env python3
"""Download official Windows installation media safely; no disk or VM operations."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OFFICIAL_SUFFIXES = (".microsoft.com", ".windows.com")
CHUNK_SIZE = 1024 * 1024
MAX_REDIRECTS = 8


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirect_count += 1
        if self.redirect_count > MAX_REDIRECTS:
            raise urllib.error.HTTPError(newurl, code, "redirect limit exceeded", headers, fp)
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != "https" or not _official_host(parsed.hostname or ""):
            raise urllib.error.HTTPError(newurl, code, "redirect left approved Microsoft domains", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _official_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host.endswith(suffix) and host != suffix[1:] for suffix in OFFICIAL_SUFFIXES)


def _valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", value or ""))


def download_official_media(url: str, destination: Path, trusted_sha256: str,
                            *, max_bytes: int = 20 * 1024**3, timeout: int = 45) -> dict:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not _official_host(parsed.hostname or ""):
        raise ValueError("Source must be HTTPS on an approved Microsoft domain.")
    if not _valid_sha256(trusted_sha256):
        raise ValueError("An independently trusted 64-character SHA-256 checksum is required.")
    if max_bytes <= 0 or timeout <= 0:
        raise ValueError("max_bytes and timeout must be positive.")
    destination = destination.resolve()
    partial = destination.with_name(destination.name + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("Destination exists; refusing to overwrite verified or existing media.")
    existing = partial.stat().st_size if partial.exists() else 0
    if existing > max_bytes:
        raise ValueError("Partial download exceeds configured size limit.")
    headers = {"User-Agent": "ElectronicBrain-WindowsMedia/1.0", "Accept-Encoding": "identity"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(SafeRedirectHandler())
    with opener.open(request, timeout=timeout) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or not _official_host(final.hostname or ""):
            raise ValueError("Final download URL is not an approved HTTPS Microsoft domain.")
        status = getattr(response, "status", response.getcode())
        if existing and status != 206:
            raise ValueError("Server did not honor Range request; refusing unsafe resume.")
        if not existing and status != 200:
            raise ValueError(f"Unexpected HTTP status: {status}")
        content_range = response.headers.get("Content-Range", "")
        if existing and not content_range.startswith(f"bytes {existing}-"):
            raise ValueError("Content-Range does not match the partial file; refusing to append.")
        declared = response.headers.get("Content-Length")
        remaining = int(declared) if declared and declared.isdigit() else None
        if remaining is not None and existing + remaining > max_bytes:
            raise ValueError("Declared download size exceeds configured maximum.")
        mode = "ab" if existing else "wb"
        with partial.open(mode) as stream:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                stream.write(chunk)
                if stream.tell() > max_bytes:
                    raise ValueError("Download exceeded configured maximum; partial file preserved.")
            stream.flush()
            os.fsync(stream.fileno())
    size = partial.stat().st_size
    digest = hashlib.sha256()
    with partial.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if size == 0:
        raise ValueError("Downloaded media is empty; partial file preserved.")
    if actual.lower() != trusted_sha256.lower():
        raise ValueError("SHA-256 mismatch; partial file preserved for diagnosis/resume, not promoted.")
    # Atomic promotion on the same filesystem. Do not overwrite a destination.
    if destination.exists():
        raise FileExistsError("Destination appeared during download; refusing overwrite.")
    os.replace(partial, destination)
    return {
        "schema": "brain.windows-official-media.v1",
        "status": "OFFICIAL_MEDIA_VERIFIED",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": url,
        "final_url": response.geturl(),
        "size_bytes": size,
        "sha256": actual,
        "checksum_source": "independently supplied trusted SHA-256",
        "destination_name": destination.name,
        "note": "URL domain and checksum were checked; this does not prove Windows boots or licensing/activation.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--trusted-sha256", required=True)
    parser.add_argument("--max-bytes", type=int, default=20 * 1024**3)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--manifest", type=Path, default=Path("windows-official-media-manifest.json"))
    args = parser.parse_args(argv)
    try:
        manifest = download_official_media(args.url, args.destination, args.trusted_sha256,
                                           max_bytes=args.max_bytes, timeout=args.timeout)
    except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": type(exc).__name__, "message": str(exc)}))
        return 2
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "size_bytes": manifest["size_bytes"],
                      "sha256": manifest["sha256"], "manifest": str(args.manifest)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
