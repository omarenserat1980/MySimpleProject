#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT"
export BRAIN_RUNTIME="BRAIN_TERMUX_EMULATOR"
export BRAIN_CLOUD_HUB_URL="${BRAIN_CLOUD_HUB_URL:-http://127.0.0.1:8787}"
python -m cinematic_image_engine_v51.cli "$@"
