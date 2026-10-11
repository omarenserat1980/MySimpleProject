#!/usr/bin/env python3
"""Read-only probe of the configured Brain Control Plane contract API.

Only GETs /openapi.json. Never calls contract issuance, sends a delivery key,
or prints the configured URL or response body.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ISSUE_PATH = "/api/brain/windows/contracts/issue"


def inspect_openapi(base_url: str, opener=None) -> dict:
    base = (base_url or "").strip().rstrip("/")
    try:
        parsed = urlsplit(base)
        valid = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        valid = False
    if not valid:
        return {"ok": False, "status": "BLOCKED", "blockers": ["CONTROL_PLANE_HTTPS_URL_INVALID"],
                "issuance_endpoint_called": False, "secret_values_emitted": False}
    request = urllib.request.Request(base + "/openapi.json", headers={"Accept": "application/json"}, method="GET")
    try:
        with (opener or urllib.request.urlopen)(request, timeout=10) as response:
            if getattr(response, "status", 200) != 200:
                raise RuntimeError("OPENAPI_HTTP_STATUS")
            document = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": "BLOCKED", "blockers": [f"OPENAPI_HTTP_{exc.code}"],
                "issuance_endpoint_called": False, "secret_values_emitted": False}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"ok": False, "status": "BLOCKED", "blockers": ["CONTROL_PLANE_UNREACHABLE"],
                "issuance_endpoint_called": False, "secret_values_emitted": False}
    except (ValueError, UnicodeError, RuntimeError):
        return {"ok": False, "status": "BLOCKED", "blockers": ["OPENAPI_RESPONSE_INVALID"],
                "issuance_endpoint_called": False, "secret_values_emitted": False}

    paths = document.get("paths") if isinstance(document, dict) else None
    methods = paths.get(ISSUE_PATH) if isinstance(paths, dict) else None
    published = isinstance(methods, dict) and "post" in methods
    blockers = [] if published else ["CONTRACT_ISSUANCE_POST_ROUTE_NOT_PUBLISHED"]
    return {
        "ok": not blockers,
        "status": "READ_ONLY_API_READY" if not blockers else "BLOCKED",
        "openapi_document_read": True,
        "contract_issuance_route_published": published,
        "blockers": blockers,
        "issuance_endpoint_called": False,
        "secret_values_emitted": False,
        "windows_boot_verified": False,
    }


def main() -> int:
    report = inspect_openapi(os.environ.get("BRAIN_WINDOWS_CONTROL_PLANE_URL", ""))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
