#!/usr/bin/env bash
set -euo pipefail
URL="${BRAIN_HEALTH_URL:-http://127.0.0.1:8000}"
curl --fail --silent --show-error --max-time 10 "$URL/healthz" >/dev/null
curl --fail --silent --show-error --max-time 10 "$URL/readyz" >/dev/null
echo "BRAIN_VPS_HEALTH=OK"