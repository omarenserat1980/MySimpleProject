#!/data/data/com.termux/files/usr/bin/bash
# Live Termux worker proof probe. Never prints the agent secret.
set -euo pipefail

BRAIN_URL="${V12_BRAIN_URL:-http://127.0.0.1:8012}"
AGENT_ID="${V12_AGENT_ID:-}"
KEY_FILE="${V12_AGENT_KEY_FILE:-${HOME}/v12-agent/agent.key}"
TTL_SECONDS="${TERMUX_AGENT_TTL_SECONDS:-15}"

if [[ -z "$AGENT_ID" ]]; then
  echo "NOT_VERIFIED: set V12_AGENT_ID to the enrolled real worker ID." >&2
  exit 2
fi
if [[ ! -s "$KEY_FILE" ]]; then
  echo "NOT_VERIFIED: agent key file missing or empty: $KEY_FILE" >&2
  exit 2
fi
if ! command -v curl >/dev/null 2>&1 || ! command -v python >/dev/null 2>&1; then
  echo "NOT_VERIFIED: requires curl and python in Termux." >&2
  exit 2
fi

AGENT_KEY="$(<"$KEY_FILE")"
if [[ -z "$AGENT_KEY" ]]; then
  echo "NOT_VERIFIED: agent key is empty." >&2
  exit 2
fi
TMP="$(mktemp -d)"
trap 'unset AGENT_KEY; rm -rf "$TMP"' EXIT
chmod 700 "$TMP"

# Secret is passed through curl config on stdin, not command-line arguments.
HTTP_CODE="$(
  printf 'header = "X-V12-Agent-Id: %s"\nheader = "X-V12-Agent-Key: %s"\nheader = "Content-Type: application/json"\n' "$AGENT_ID" "$AGENT_KEY" |
  curl --silent --show-error --max-time 10 --config - \
    --output "$TMP/heartbeat.json" --write-out '%{http_code}' \
    --request POST --data '{"metadata":{"source":"termux-live-proof-probe","probe_version":1}}' \
    "${BRAIN_URL%/}/api/device/heartbeat"
)"
unset AGENT_KEY
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "NOT_VERIFIED: heartbeat endpoint returned HTTP $HTTP_CODE."
  cat "$TMP/heartbeat.json"
  exit 1
fi

# Query the authenticated status endpoint. Read the key file again only for this request.
AGENT_KEY="$(<"$KEY_FILE")"
STATUS_CODE="$(
  printf 'header = "X-V12-Agent-Id: %s"\nheader = "X-V12-Agent-Key: %s"\n' "$AGENT_ID" "$AGENT_KEY" |
  curl --silent --show-error --max-time 10 --config - \
    --output "$TMP/status.json" --write-out '%{http_code}' \
    "${BRAIN_URL%/}/api/device/agent-status/$AGENT_ID"
)"
unset AGENT_KEY
if [[ "$STATUS_CODE" != "200" ]]; then
  echo "NOT_VERIFIED: status endpoint returned HTTP $STATUS_CODE."
  cat "$TMP/status.json"
  exit 1
fi

python - "$TMP/heartbeat.json" "$TMP/status.json" "$AGENT_ID" "$TTL_SECONDS" <<'PY'
import json, sys
heartbeat_path, status_path, agent_id, configured_ttl = sys.argv[1:]
with open(heartbeat_path, encoding="utf-8") as f:
    heartbeat = json.load(f)
with open(status_path, encoding="utf-8") as f:
    status = json.load(f)
if heartbeat.get("ok") is not True or heartbeat.get("status") != "HEARTBEAT":
    raise SystemExit("NOT_VERIFIED: server did not acknowledge heartbeat.")
if status.get("ok") is not True or status.get("agent_id") != agent_id:
    raise SystemExit("NOT_VERIFIED: server status identity mismatch.")
ttl = int(status.get("ttl_seconds", 0))
age = float(status.get("age_seconds", float("inf")))
if status.get("online") is not True or status.get("state") != "ONLINE" or ttl < 1 or age > ttl:
    raise SystemExit("NOT_VERIFIED: heartbeat is stale or status is not ONLINE.")
print(json.dumps({
    "verified": True,
    "gate": "AUTHENTICATED_HEARTBEAT_LIVE",
    "agent_id": agent_id,
    "age_seconds": age,
    "server_ttl_seconds": ttl,
    "configured_client_ttl_seconds": int(configured_ttl),
    "evidence_limit": "This proves authenticated API heartbeat liveness only; not task execution, physical hardware attestation, mining, or revenue."
}, sort_keys=True))
PY
