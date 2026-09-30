#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export BRAIN_FILM_MEDIA_ROOT="${BRAIN_FILM_MEDIA_ROOT:-$ROOT/brain_v12/film_hub/media}"
mkdir -p "$BRAIN_FILM_MEDIA_ROOT"
cd "$ROOT/brain_v12/film_hub"
exec dotnet run --urls "${BRAIN_FILM_HUB_URL:-http://127.0.0.1:8088}"
