#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${BRAIN_APP_DIR:-/opt/brain-cloud}"
REPO="${BRAIN_REPO:-https://github.com/omarenserat1980/MySimpleProject.git}"
if [[ $EUID -ne 0 ]]; then echo "Run as root."; exit 1; fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y git
mkdir -p "$APP_DIR"
if [[ ! -d "$APP_DIR/.git" ]]; then git clone "$REPO" "$APP_DIR"; else git -C "$APP_DIR" fetch origin main && git -C "$APP_DIR" reset --hard origin/main; fi
cd "$APP_DIR/cloud"
if [[ ! -f .env ]]; then cp .env.production.example .env; chmod 600 .env; echo "Set BRAIN_CONTROL_TOKEN in $APP_DIR/cloud/.env"; fi
docker compose -f docker-compose.production.yml pull
docker compose -f docker-compose.production.yml up -d
docker compose -f docker-compose.production.yml ps
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz