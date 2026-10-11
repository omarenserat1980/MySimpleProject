#!/usr/bin/env bash
# Discover public executor/registry API route names from the deployed Brain Control Plane.
# This is read-only: it never authenticates, prints response bodies, reads secrets, or issues contracts.
set -Eeuo pipefail
umask 077
BASE_URL="${BRAIN_WINDOWS_CONTROL_PLANE_URL:-https://brain-control-plane-main.onrender.com}"
python3 - "$BASE_URL" <<'PY'
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

base = sys.argv[1].strip().rstrip("/")
try:
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        print("DISCOVERY=BLOCKED")
        print("REASON=INVALID_HTTPS_BASE_URL")
        raise SystemExit(2)
except Exception:
    print("DISCOVERY=BLOCKED")
    print("REASON=INVALID_HTTPS_BASE_URL")
    raise SystemExit(2)

url = base + "/openapi.json"
try:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "ElectronicBrain-ReadOnly-Route-Discovery/1.0"})
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            print("DISCOVERY=BLOCKED")
            print("REASON=OPENAPI_HTTP_STATUS")
            print("HTTP_STATUS=" + str(response.status))
            raise SystemExit(3)
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            print("DISCOVERY=BLOCKED")
            print("REASON=OPENAPI_TOO_LARGE")
            raise SystemExit(3)
    spec = json.loads(raw.decode("utf-8"))
except HTTPError as exc:
    print("DISCOVERY=BLOCKED")
    print("REASON=OPENAPI_HTTP_ERROR")
    print("HTTP_STATUS=" + str(exc.code))
    raise SystemExit(3)
except (URLError, TimeoutError, OSError, ValueError, UnicodeError):
    print("DISCOVERY=BLOCKED")
    print("REASON=OPENAPI_UNAVAILABLE_OR_INVALID")
    raise SystemExit(3)

paths = sorted(spec.get("paths", {}))
matches = [p for p in paths if any(term in p.lower() for term in ("executor", "registry", "attestation", "windows/contracts", "windows/cloud"))]
print("DISCOVERY=PASS")
print("OPENAPI_PATH_COUNT=" + str(len(paths)))
print("RELEVANT_ROUTE_COUNT=" + str(len(matches)))
for route in matches:
    methods = sorted(str(m).upper() for m in spec.get("paths", {}).get(route, {}) if str(m).lower() in {"get","post","put","patch","delete"})
    print("ROUTE=" + ",".join(methods) + " " + route)
if not matches:
    print("NEXT=Executor registry is not advertised in the public OpenAPI schema; obtain the actual registry base URL from the authorized executor owner.")
else:
    print("NOTE=Route discovery is not authentication, registry enrollment, contract issuance, or boot proof.")
PY
