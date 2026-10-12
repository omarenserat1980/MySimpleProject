#!/usr/bin/env bash
set -Eeuo pipefail

# Industrial Brain Client connector.
# Single-path connection: readiness -> heartbeat -> bounded retry -> offline queue.
# No workflow dispatches, no parallel repair loops, no secret values in logs.

RUNTIME_URL="${BRAIN_RUNTIME_URL:-http://127.0.0.1:8012}"
READINESS_PATH="${BRAIN_READINESS_PATH:-/api/system/readiness}"
HEARTBEAT_PATH="${BRAIN_HEARTBEAT_PATH:-/api/device/heartbeat}"
CLIENT_ID="${BRAIN_CLIENT_ID:-industrial-client-01}"
QUEUE_FILE="${BRAIN_CLIENT_QUEUE:-brain6_artifacts/industrial-client/queue.jsonl}"
MAX_RETRIES="${BRAIN_CONNECT_RETRIES:-3}"
CONNECT_TIMEOUT="${BRAIN_CONNECT_TIMEOUT:-5}"
AGENT_KEY="${BRAIN_AGENT_KEY:-}"

mkdir -p "$(dirname "$QUEUE_FILE")"

json_escape() {
  python3 - "$1" <<'PY'
import json,sys
print(json.dumps(sys.argv[1]))
PY
}

queue_event() {
  local status="$1" detail="$2"
  printf '{"client_id":%s,"status":%s,"detail":%s,"ts":%s}\n'     "$(json_escape "$CLIENT_ID")"     "$(json_escape "$status")"     "$(json_escape "$detail")"     "$(date +%s)" >> "$QUEUE_FILE"
}

echo "[industrial-client] runtime=$RUNTIME_URL client=$CLIENT_ID"

readiness=""
for attempt in $(seq 1 "$MAX_RETRIES"); do
  if readiness="$(curl -fsS --connect-timeout "$CONNECT_TIMEOUT" --max-time "$CONNECT_TIMEOUT"       "$RUNTIME_URL$READINESS_PATH" 2>/dev/null)"; then
    echo "[industrial-client] READINESS=OK attempt=$attempt"
    break
  fi
  echo "[industrial-client] READINESS=RETRY attempt=$attempt/$MAX_RETRIES"
  sleep 1
done

if [[ -z "$readiness" ]]; then
  queue_event "OFFLINE_QUEUED" "Brain runtime unavailable"
  echo "[industrial-client] status=OFFLINE_QUEUED queue=$QUEUE_FILE"
  exit 20
fi

# Heartbeat is optional at the transport layer: if the endpoint is not deployed yet,
# preserve the verified readiness result and queue the heartbeat instead of failing
# the whole client.
heartbeat_body=$(printf '{"agent_id":%s,"status":"ONLINE","metadata":{"client_type":"industrial","client_version":"1","transport":"http"}}'   "$(json_escape "$CLIENT_ID")")

heartbeat_headers=(-H "Content-Type: application/json")
if [[ -n "$AGENT_KEY" ]]; then
  heartbeat_headers+=(-H "Authorization: Bearer $AGENT_KEY")
fi

if curl -fsS --connect-timeout "$CONNECT_TIMEOUT" --max-time "$CONNECT_TIMEOUT"     -X POST "${heartbeat_headers[@]}"     --data "$heartbeat_body"     "$RUNTIME_URL$HEARTBEAT_PATH" >/dev/null 2>&1; then
  queue_event "CONNECTED_VERIFIED" "readiness and heartbeat verified"
  echo "[industrial-client] status=CONNECTED_VERIFIED"
  exit 0
fi

queue_event "READINESS_OK_HEARTBEAT_PENDING" "runtime reachable; heartbeat endpoint unavailable or rejected"
echo "[industrial-client] status=READINESS_OK_HEARTBEAT_PENDING queue=$QUEUE_FILE"
exit 21
