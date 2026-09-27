#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT"
if command -v termux-diffusion >/dev/null 2>&1; then export EB_IMAGE_ADAPTER="termux-diffusion"; fi
python -m cinematic_image_engine_v51.cli "$@"