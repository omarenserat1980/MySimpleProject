#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${BRAIN_APP_DIR:-/opt/brain-cloud}"
cd "$APP_DIR"
git fetch origin main
git reset --hard origin/main
cd cloud
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
docker compose -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:8000/healthz