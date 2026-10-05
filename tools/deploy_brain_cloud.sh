#!/usr/bin/env bash
set -euo pipefail

: "${BRAIN_CLOUD_HOST:?Set BRAIN_CLOUD_HOST to the cloud VM hostname or IP}"
: "${BRAIN_CLOUD_USER:?Set BRAIN_CLOUD_USER to the SSH user}"
: "${BRAIN_CLOUD_REPO_DIR:=/opt/brain}"

SSH_TARGET="${BRAIN_CLOUD_USER}@${BRAIN_CLOUD_HOST}"

ssh "${SSH_TARGET}" "test -d '${BRAIN_CLOUD_REPO_DIR}'"
ssh "${SSH_TARGET}" "cd '${BRAIN_CLOUD_REPO_DIR}' && ./tools/brain_cloud_preflight.sh"
ssh "${SSH_TARGET}" "cd '${BRAIN_CLOUD_REPO_DIR}' && docker compose -f docker-compose.brain-cloud.yml up -d --build"

echo "BRAIN_CLOUD_DEPLOY=STARTED"

for attempt in $(seq 1 20); do
  if ssh "${SSH_TARGET}" "cd '${BRAIN_CLOUD_REPO_DIR}' && curl -fsS http://127.0.0.1:8012/health | grep -q '"state": "RUNNING"'"; then
    echo "BRAIN_CLOUD_RUNTIME=VERIFIED"
    ssh "${SSH_TARGET}" "cd '${BRAIN_CLOUD_REPO_DIR}' && curl -fsS http://127.0.0.1:8012/health"
    exit 0
  fi
  sleep 5
done

echo "BRAIN_CLOUD_RUNTIME=NOT_VERIFIED" >&2
ssh "${SSH_TARGET}" "cd '${BRAIN_CLOUD_REPO_DIR}' && docker compose -f docker-compose.brain-cloud.yml ps"
ssh "${SSH_TARGET}" "cd '${BRAIN_CLOUD_REPO_DIR}' && docker compose -f docker-compose.brain-cloud.yml logs --tail=120 brain-cloud-runtime" || true
exit 30
