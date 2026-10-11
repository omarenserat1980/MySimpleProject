"""Safe discovery of publicly available, explicitly licensed open-source repositories.

This module discovers candidate tools; it never clones, installs, imports, or executes
third-party code. Integration requires a separate reviewed and authorized change.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Any

import httpx


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
OPEN_SOURCE_SPDX_IDS = frozenset({
    "0BSD", "AFL-3.0", "AGPL-3.0", "Apache-2.0", "Artistic-2.0",
    "BSD-2-Clause", "BSD-3-Clause", "BSL-1.0", "CDDL-1.0", "EPL-1.0",
    "EPL-2.0", "EUPL-1.1", "EUPL-1.2", "GPL-2.0", "GPL-3.0",
    "ISC", "LGPL-2.1", "LGPL-3.0", "MIT", "MPL-2.0", "MS-PL",
    "OSL-3.0", "PostgreSQL", "Unlicense", "WTFPL", "Zlib",
})
_LANGUAGE_RE = re.compile(r"^[A-Za-z0-9_+#.-]{1,40}$")


class OpenSourceToolRegistry:
    """Search GitHub's public repository index and return license-filtered candidates."""

    def __init__(self, ttl_seconds: int = 300, timeout_seconds: float = 10.0) -> None:
        self.ttl_seconds = max(30, int(ttl_seconds))
        self.timeout_seconds = max(2.0, float(timeout_seconds))
        self._cache: dict[tuple[str, str, int], tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _clean_query(query: str) -> str:
        cleaned = " ".join(str(query or "").split())
        return cleaned[:100] or "developer tools"

    @staticmethod
    def _clean_language(language: str | None) -> str | None:
        value = str(language or "").strip()
        if not value:
            return None
        if not _LANGUAGE_RE.fullmatch(value):
            raise ValueError("INVALID_LANGUAGE_FILTER")
        return value

    @staticmethod
    def _public_item(item: dict[str, Any]) -> dict[str, Any] | None:
        license_data = item.get("license")
        spdx = license_data.get("spdx_id") if isinstance(license_data, dict) else None
        if spdx not in OPEN_SOURCE_SPDX_IDS:
            return None
        full_name = str(item.get("full_name") or "").strip()
        html_url = str(item.get("html_url") or "").strip()
        if not full_name or not html_url.startswith("https://github.com/"):
            return None
        return {
            "id": full_name.lower(),
            "name": str(item.get("name") or full_name.rsplit("/", 1)[-1]),
            "full_name": full_name,
            "description": str(item.get("description") or "")[:500],
            "url": html_url,
            "default_branch": str(item.get("default_branch") or "main"),
            "language": item.get("language"),
            "stars": int(item.get("stargazers_count") or 0),
            "license": spdx,
            "topics": [str(topic) for topic in (item.get("topics") or [])[:20]],
            "updated_at": item.get("updated_at"),
            "archived": bool(item.get("archived")),
            "fork": bool(item.get("fork")),
            "status": "DISCOVERED_NOT_INSTALLED",
            "executable": False,
            "security_review_required": True,
        }

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "open-source-tool-discovery",
            "provider": "GitHub public repository search API",
            "license_filter": "recognized SPDX identifiers only",
            "recognized_license_count": len(OPEN_SOURCE_SPDX_IDS),
            "cache_ttl_seconds": self.ttl_seconds,
            "auto_install": False,
            "auto_execute": False,
        }

    def search(
        self, query: str = "developer tools", language: str | None = None, limit: int = 10
    ) -> dict[str, Any]:
        clean_query = self._clean_query(query)
        try:
            clean_language = self._clean_language(language)
        except ValueError:
            return {"ok": False, "status": "INVALID_LANGUAGE_FILTER", "tools": []}
        try:
            clean_limit = max(1, min(20, int(limit)))
        except (TypeError, ValueError):
            clean_limit = 10

        cache_key = (clean_query.casefold(), (clean_language or "").casefold(), clean_limit)
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and now - cached[0] < self.ttl_seconds:
                result = dict(cached[1])
                result["cached"] = True
                return result

        api_query = f"{clean_query} in:name,description,readme"
        if clean_language:
            api_query += f" language:{clean_language}"
        params = {
            "q": api_query,
            "per_page": min(60, max(20, clean_limit * 3)),
            "sort": "stars",
            "order": "desc",
        }
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Electronic-Brain-Open-Source-Discovery",
        }
        try:
            response = httpx.get(
                GITHUB_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            raw_items = payload.get("items", []) if isinstance(payload, dict) else []
            tools = []
            seen = set()
            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                public_item = self._public_item(raw)
                if public_item and public_item["id"] not in seen:
                    seen.add(public_item["id"])
                    tools.append(public_item)
                if len(tools) >= clean_limit:
                    break
            result = {
                "ok": True,
                "status": "COMPLETED",
                "query": clean_query,
                "language": clean_language,
                "count": len(tools),
                "tools": tools,
                "cached": False,
                "source": GITHUB_SEARCH_URL,
                "note": "Repositories are discovery candidates, not installed or security-approved tools.",
            }
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            result = {
                "ok": False,
                "status": "RATE_LIMITED" if status_code in (403, 429) else "UPSTREAM_ERROR",
                "http_status": status_code,
                "tools": [],
            }
        except (httpx.HTTPError, ValueError, TypeError):
            result = {"ok": False, "status": "UPSTREAM_ERROR", "tools": []}

        if result["ok"]:
            with self._lock:
                self._cache[cache_key] = (time.monotonic(), result)
        return result
