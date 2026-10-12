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
            # Emit only an allowlist of non-secret scalar health fields and counts.
            for key in ("ready", "ok", "verified"):
                if isinstance(obj.get(key), bool):
                    print(f"{label}_{key.upper()}={str(obj[key]).lower()}")
            for key in ("status", "reason"):
                value = obj.get(key)
                if isinstance(value, str):
                    safe = "".join(ch for ch in value[:100] if ch.isalnum() or ch in " _-.:/")
                    print(f"{label}_{key.upper()}={safe or '(empty)'}")
            for key in ("missing", "nodes", "rejected", "checks"):
                value = obj.get(key)
                if isinstance(value, (list, dict)):
                    print(f"{label}_{key.upper()}_COUNT={len(value)}")
                elif isinstance(value, int) and not isinstance(value, bool):
                    print(f"{label}_{key.upper()}_COUNT={value}")
                # Missing item names are configuration identifiers, not values.
                if key == "missing" and isinstance(value, list):
                    safe_items = []
                    for item in value[:30]:
                        if isinstance(item, str):
                            safe = "".join(ch for ch in item[:120] if ch.isalnum() or ch in "_-.:/")
                            if safe:
                                safe_items.append(safe)
                        elif isinstance(item, dict):
                            name = item.get("name") or item.get("key") or item.get("id") or item.get("code")
                            if isinstance(name, str):
                                safe = "".join(ch for ch in name[:120] if ch.isalnum() or ch in "_-.:/")
                                if safe:
                                    safe_items.append(safe)
                    if safe_items:
                        print(f"{label}_MISSING_ITEMS={','.join(safe_items)}")
                if key == "checks":
                    entries = list(value.items()) if isinstance(value, dict) else list(enumerate(value)) if isinstance(value, list) else []
                    for check_key, check in entries[:30]:
                        if isinstance(check, dict):
                            name = check.get("name") or check.get("key") or check.get("id") or check.get("code") or str(check_key)
                            safe_name = "".join(ch for ch in str(name)[:80] if ch.isalnum() or ch in "_-.:/")
                            state_parts = []
                            for field in ("ok", "ready", "configured", "passed", "status", "reason"):
                                field_value = check.get(field)
                                if isinstance(field_value, bool):
                                    state_parts.append(f"{field}={str(field_value).lower()}")
                                elif isinstance(field_value, str):
                                    safe_value = "".join(ch for ch in field_value[:80] if ch.isalnum() or ch in "_-.:/ ")
                                    state_parts.append(f"{field}={safe_value}")
                            if state_parts:
                                print(f"{label}_CHECK_{safe_name}=" + ";".join(state_parts))
                        elif isinstance(check, bool):
                            print(f"{label}_CHECK_{check_key}={str(check).lower()}")
            for key in ("executor", "provider_readiness", "capability", "policy"):
                value = obj.get(key)
                if isinstance(value, dict):
                    nested_keys = sorted(str(k) for k in value.keys())
                    print(f"{label}_{key.upper()}_KEYS={','.join(nested_keys[:25]) or '(none)'}")
                    for field in ("ready", "ok", "verified", "configured"):
                        if isinstance(value.get(field), bool):
                            print(f"{label}_{key.upper()}_{field.upper()}={str(value[field]).lower()}")
                    for field in ("status", "reason", "provider"):
                        item = value.get(field)
                        if isinstance(item, str):
                            safe = "".join(ch for ch in item[:100] if ch.isalnum() or ch in "_-.:/ ")
                            print(f"{label}_{key.upper()}_{field.upper()}={safe or '(empty)'}")
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
