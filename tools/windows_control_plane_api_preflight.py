#!/usr/bin/env python3
"""Read-only probe of the configured Brain Control Plane contract API.

Only GETs /openapi.json. It never invokes the contract-issuance POST endpoint,
never sends a delivery key, and never prints the configured URL or response body.
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
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return {"ok": False, "status": "BLOCKED", "blockers": ["CONTROL_PLANE_HTTPS_URL_INVALID"],
                "issuance_endpoint_called": False, "secret_values_emitted": False}
    open_url = base + "/openapi.json"
    request = urllib.request.Request(open_url, headers={"Accept": "application/json"}, method="GET")
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request, timeout=10) as response:
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
    has_issue_post = isinstance(methods, dict) and "post" in methods
    blockers = [] if has_issue_post else ["CONTRACT_ISSUANCE_POST_ROUTE_NOT_PUBLISHED"]
    return {
        "ok": not blockers,
        "status": "READ_ONLY_API_READY" if not blockers else "BLOCKED",
        "openapi_document_read": True,
        "contract_issuance_route_published": has_issue_post,
        "blockers": blockers,
        "issuance_endpoint_called": False,
        "secret_values_emitted": False,
        "windows_boot_verified": False,
    }


def main() -> int:
    result = inspect_openapi(os.environ.get("BRAIN_WINDOWS_CONTROL_PLANE_URL", ""))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
