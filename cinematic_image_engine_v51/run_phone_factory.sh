#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"
python -m cinematic_image_engine_v51.phone_executor_probe
exec python -m cinematic_image_engine_v51.cli "$@"
