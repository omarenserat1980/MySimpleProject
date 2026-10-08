#!/usr/bin/env bash
set -Eeuo pipefail

# BRAIN-CLIENT-ARKAN-ISO-01 request sender.
# This submits a client request; Brain alone selects and dispatches the
# existing primary ISO workflow. No arbitrary workflow name is accepted.

RUNTIME_URL="${BRAIN_RUNTIME_URL:-http://127.0.0.1:8012}"
CLIENT_ID="${BRAIN_CLIENT_ID:-BRAIN-CLIENT-ARKAN-ISO-01}"
CLIENT_KEY="${BRAIN_CLIENT_KEY:-}"
if [[ -z "$CLIENT_KEY" && -n "${BRAIN_INDUSTRIAL_CLIENT_KEY_FILE:-}" && -r "${BRAIN_INDUSTRIAL_CLIENT_KEY_FILE}" ]]; then
  CLIENT_KEY="$(cat "$BRAIN_INDUSTRIAL_CLIENT_KEY_FILE")"
fi
TARGET="${BRAIN_CLIENT_TARGET:-}"

if [[ -z "$CLIENT_KEY" ]]; then
  echo "CLIENT_KEY_REQUIRED" >&2
  exit 2
fi

payload=$(python3 - "$CLIENT_ID" "$TARGET" <<'PY'
import json,sys
print(json.dumps({
    "client_id": sys.argv[1],
    "request": "LOAD_AND_BOOT_BRAIN_ISO",
    "target": sys.argv[2],
}))
PY
)

curl -fsS --connect-timeout 10 --max-time 30 \
  -X POST "$RUNTIME_URL/api/industrial-clients/request" \
  -H "Content-Type: application/json" \
  -H "X-Brain-Client-Key: $CLIENT_KEY" \
  --data "$payload"
