#!/bin/bash
set -euo pipefail
exec > >(tee -a /var/log/brain-cloud-bootstrap.log) 2>&1

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git docker.io docker-compose-plugin
systemctl enable --now docker

mkdir -p /opt/MySimpleProject /var/lib/brain

if [ ! -d /opt/MySimpleProject/.git ]; then
  git clone https://github.com/omarenserat1980/MySimpleProject.git /opt/MySimpleProject
else
  cd /opt/MySimpleProject
  git fetch --all --prune
  git reset --hard origin/main
fi

cd /opt/MySimpleProject
printf '%s
' '{"status":"BOOTSTRAPPING","service":"brain-cloud-worker"}' >/var/lib/brain/host-status.json

docker compose -f brain_v12/brain_git/compose.yml up -d
docker compose -f brain_v12/cloud_worker/compose.yml up -d --build

install -m 0644 brain_v12/cloud_worker/brain-cloud-worker.service /etc/systemd/system/brain-cloud-worker.service
systemctl daemon-reload
systemctl enable --now brain-cloud-worker

printf '%s
' '{"status":"RUNNING","service":"brain-cloud-worker"}' >/var/lib/brain/host-status.json
docker ps --format '{{.Names}} {{.Status}}' >/var/lib/brain/docker-status.txt
