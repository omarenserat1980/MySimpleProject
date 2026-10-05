#!/usr/bin/env bash
set -euo pipefail

command -v docker >/dev/null || { echo "DOCKER_MISSING"; exit 10; }
docker compose version >/dev/null || { echo "DOCKER_COMPOSE_MISSING"; exit 11; }

test -f Dockerfile.brain-cloud
test -f docker-compose.brain-cloud.yml

docker compose -f docker-compose.brain-cloud.yml config >/dev/null

echo "BRAIN_CLOUD_STACK=CONFIG_VALID"
