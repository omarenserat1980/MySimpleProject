#!/usr/bin/env bash
set -euo pipefail

# Run Brain Cloud on a user-owned Linux host.
# GitHub is source/audit only; this node is the execution runtime.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

./tools/brain_cloud_preflight.sh
docker compose -f docker-compose.brain-cloud.yml up -d --build

echo "Waiting for Brain Cloud worker attestation..."
for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8012/health | grep -q '"state": "RUNNING"'; then
    echo "BRAIN_CLOUD_NODE=VERIFIED"
    curl -fsS http://127.0.0.1:8012/health
    exit 0
  fi
  sleep 5
done

echo "BRAIN_CLOUD_NODE=NOT_VERIFIED" >&2
docker compose -f docker-compose.brain-cloud.yml ps
docker compose -f docker-compose.brain-cloud.yml logs --tail=120 brain-cloud-runtime || true
exit 30
