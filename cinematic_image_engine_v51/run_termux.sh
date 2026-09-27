#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")/.."
python -m cinematic_image_engine_v51.cli "$@"
