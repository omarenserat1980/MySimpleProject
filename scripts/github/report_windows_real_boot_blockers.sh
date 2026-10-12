#!/usr/bin/env bash
# Read-only one-command report for the real Windows launch blockers.
# Does not provision Azure, issue contracts, enroll guests, or print secret values.
set -Eeuo pipefail
umask 077
REPO="omarenserat1980/MySimpleProject"
BRANCH="${BRAIN_WINDOWS_BRANCH:-fix/windows-control-plane-public-url-default}"
CONTROL_URL="${BRAIN_WINDOWS_CONTROL_PLANE_URL:-https://brain-control-plane-main.onrender.com}"
command -v python3 >/dev/null 2>&1 || { echo "BLOCKED=python3_required"; exit 2; }
python3 - "$REPO" "$BRANCH" "$CONTROL_URL" <<'PY'
import json, sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

repo, branch, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
if not branch or any(c in branch for c in "\r\n"):
    print("BRANCH=INVALID"); raise SystemExit(2)
p = urlsplit(base)
if p.scheme != "https" or not p.hostname or p.username or p.password or p.query or p.fragment:
    print("CONTROL_PLANE_URL=INVALID_HTTPS_URL"); raise SystemExit(2)

def get_json(url, label):
    req = Request(url, headers={"Accept":"application/vnd.github+json","User-Agent":"ElectronicBrain-Launch-Blocker-Report/1.0"})
    try:
        with urlopen(req, timeout=20) as r:
            data = r.read(2_000_001)
            if len(data) > 2_000_000:
                print(label + "=BLOCKED_TOO_LARGE"); return None
            return json.loads(data.decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError):
        print(label + "=UNAVAILABLE"); return None

api = f"https://api.github.com/repos/{repo}/actions/runs?branch={quote(branch, safe='/')}&per_page=100"
runs = get_json(api, "GITHUB_ACTIONS")
if isinstance(runs, dict):
    matches = [r for r in runs.get("workflow_runs", [])
               if r.get("path") == ".github/workflows/brain-windows-azure-readonly-preflight.yml"]
    matches.sort(key=lambda r: r.get("run_started_at") or r.get("created_at") or "", reverse=True)
    if matches:
        run = matches[0]
        print("AZURE_PREFLIGHT_RUN_ID=" + str(run.get("id", "unknown")))
        print("AZURE_PREFLIGHT_STATUS=" + str(run.get("status", "unknown")))
        print("AZURE_PREFLIGHT_CONCLUSION=" + str(run.get("conclusion", "unknown")))
        print("AZURE_PREFLIGHT_COMMIT=" + str(run.get("head_sha", "unknown")))
        print("AZURE_PREFLIGHT_URL=" + str(run.get("html_url", "")))
    else:
        print("AZURE_PREFLIGHT_RUN=NOT_FOUND")
else:
    print("AZURE_PREFLIGHT_RUN=UNAVAILABLE")

failed = False
routes = (
    ("/api/brain/windows/cloud/readiness", "CLOUD"),
    ("/api/brain/windows/cloud/secrets/readiness", "SECRETS"),
    ("/api/brain/windows/cloud/status", "GUEST"),
)
for route, label in routes:
    req = Request(base + route, headers={"Accept":"application/json","User-Agent":"ElectronicBrain-Launch-Blocker-Report/1.0"})
    try:
        with urlopen(req, timeout=15) as r:
            raw = r.read(1_000_001)
            if len(raw) > 1_000_000: raise ValueError("too large")
            obj = json.loads(raw.decode("utf-8"))
            if not isinstance(obj, dict): raise ValueError("not object")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError):
        print(label + "_ENDPOINT=UNAVAILABLE")
        failed = True
        continue
    print(label + "_HTTP=200")
    if label == "CLOUD":
        print("CLOUD_READY=" + str(obj.get("ready", False)).lower())
        for key in ("status", "reason"):
            value = obj.get(key)
            if isinstance(value, str):
                safe = "".join(c for c in value[:100] if c.isalnum() or c in "_-.:/ ")
                print("CLOUD_" + key.upper() + "=" + (safe or "UNKNOWN"))
        if obj.get("ready") is not True: failed = True
    elif label == "SECRETS":
        print("SECRETS_READY=" + str(obj.get("ok", False)).lower())
        missing = obj.get("missing", [])
        names = []
        if isinstance(missing, list):
            for item in missing[:30]:
                if isinstance(item, str):
                    safe = "".join(c for c in item[:80] if c.isalnum() or c in "_-.:/")
                    if safe: names.append(safe)
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("key") or item.get("id") or item.get("code")
                    if isinstance(name, str):
                        safe = "".join(c for c in name[:80] if c.isalnum() or c in "_-.:/")
                        if safe: names.append(safe)
        print("SECRETS_MISSING_COUNT=" + str(len(missing) if isinstance(missing, list) else "unknown"))
        print("SECRETS_MISSING_ITEMS=" + (",".join(names) if names else "none_reported"))
        if obj.get("ok") is not True: failed = True
    else:
        print("GUEST_VERIFIED=" + str(obj.get("verified", False)).lower())
        nodes = obj.get("nodes", [])
        print("GUEST_NODE_COUNT=" + str(len(nodes) if isinstance(nodes, list) else "unknown"))
        print("GUEST_STATUS=" + str(obj.get("status", "unknown"))[:100])
        if obj.get("verified") is not True: failed = True

print("FINAL=" + ("BLOCKED" if failed else "READINESS_PASS_BOOT_STILL_REQUIRES_SAME_RUN_GUEST_EVIDENCE"))
if failed:
    raise SystemExit(4)
PY
