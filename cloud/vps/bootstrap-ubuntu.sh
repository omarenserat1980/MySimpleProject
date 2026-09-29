#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${BRAIN_APP_DIR:-/opt/brain-cloud}"
if [[ $EUID -ne 0 ]]; then echo "Run as root: sudo bash bootstrap-ubuntu.sh"; exit 1; fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl git ufw openssh-client
if ! command -v docker >/dev/null 2>&1; then curl -fsSL https://get.docker.com | sh; fi
systemctl enable --now docker
apt-get install -y docker-compose-plugin
mkdir -p "$APP_DIR"
chmod 750 "$APP_DIR"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
docker --version
docker compose version
echo "Brain VPS base runtime ready: $APP_DIR"