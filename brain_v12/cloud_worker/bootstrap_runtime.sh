#!/usr/bin/env bash
set -euo pipefail

ROOT="${BRAIN_RUNTIME_ROOT:-$HOME/MySimpleProject}"
COMPOSE_FILE="$ROOT/brain_v12/cloud_worker/docker-compose.runtime.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "BRAIN_RUNTIME_ERROR: Docker is required on the host."
  exit 2
fi
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "BRAIN_RUNTIME_ERROR: repository/runtime compose file not found: $COMPOSE_FILE"
  exit 3
fi

if [ -z "${BRAIN_CLOUD_API_KEY:-}" ]; then
  echo "BRAIN_RUNTIME_ERROR: set BRAIN_CLOUD_API_KEY before starting the runtime."
  exit 4
fi

cd "$ROOT"
docker compose -f "$COMPOSE_FILE" up -d --build
sleep 3

if ! curl -fsS http://127.0.0.1:8080/health >/tmp/brain-runtime-health.json; then
  echo "BRAIN_RUNTIME_ERROR: local health check failed."
  exit 5
fi

cat /tmp/brain-runtime-health.json
echo
echo "BRAIN_RUNTIME_READY: local runtime is healthy on http://127.0.0.1:8080"
echo "NEXT: place an authorized HTTPS reverse proxy/tunnel in front of port 8080."
