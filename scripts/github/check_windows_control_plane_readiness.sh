#!/usr/bin/env bash
# Read-only, secret-safe diagnostics for public Brain Windows Control Plane endpoints.
# Does not print response bodies, inspect credentials, issue contracts, or start a VM.
set -Eeuo pipefail
umask 077
BASE_URL="${BRAIN_WINDOWS_CONTROL_PLANE_URL:-https://brain-control-plane-main.onrender.com}"
command -v python3 >/dev/null 2>&1 || { printf '%s\n' 'BLOCKED=python3_required'; exit 2; }
python3 - "$BASE_URL" <<'PY'
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

base = sys.argv[1].strip().rstrip("/")
try:
    parsed = urlsplit(base)
    valid = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
except Exception:
    valid = False
if not valid:
    print("CONTROL_PLANE_DIAGNOSTICS=BLOCKED")
    print("REASON=INVALID_HTTPS_BASE_URL")
    raise SystemExit(2)

routes = (
    ("/api/brain/windows/cloud/readiness", "CLOUD_READINESS"),
    ("/api/brain/windows/cloud/secrets/readiness", "SECRETS_READINESS"),
    ("/api/brain/windows/cloud/status", "CLOUD_STATUS"),
)
failed = 0
for route, label in routes:
    req = Request(base + route, headers={"Accept": "application/json", "User-Agent": "ElectronicBrain-ControlPlane-Readiness/1.0"})
    try:
        with urlopen(req, timeout=15) as response:
            code = response.status
            raw = response.read(1_000_001)
            too_large = len(raw) > 1_000_000
    except HTTPError as exc:
        code, raw, too_large = exc.code, b"", False
    except (URLError, TimeoutError, OSError):
        print(f"{label}=UNREACHABLE")
        failed += 1
        continue
    print(f"{label}_HTTP_STATUS={code}")
    if too_large:
        print(f"{label}_JSON=BLOCKED_TOO_LARGE")
        failed += 1
        continue
    try:
        obj = json.loads(raw.decode("utf-8"))
        if isinstance(obj, dict):
            # Only expose the names of fields, never response values or bodies.
            keys = sorted(str(k) for k in obj.keys())
            print(f"{label}_JSON=VALID")
            print(f"{label}_TOP_LEVEL_KEYS={','.join(keys[:40]) or '(none)'}")
        else:
            print(f"{label}_JSON=VALID_NON_OBJECT")
    except (ValueError, UnicodeError):
        print(f"{label}_JSON=NON_JSON_OR_EMPTY")
    if not 200 <= code < 300:
        failed += 1
print("CONTROL_PLANE_DIAGNOSTICS=" + ("PASS" if failed == 0 else "BLOCKED"))
print("NOTE=HTTP reachability is not proof of authorization, executor readiness, signed contract issuance, or guest boot.")
raise SystemExit(0 if failed == 0 else 3)
PY
