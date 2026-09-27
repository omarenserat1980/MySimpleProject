#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
export EB_IMAGE_ADAPTER="termux-diffusion"
export EB_DIFFUSION_MODEL="${EB_DIFFUSION_MODEL:-cyberrealistic-lcm}"
export EB_DIFFUSION_STEPS="${EB_DIFFUSION_STEPS:-6}"
export EB_DIFFUSION_THREADS="${EB_DIFFUSION_THREADS:-4}"
python termux_agent/electronic_brain_5s_factory.py
