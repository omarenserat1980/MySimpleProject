#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
pkg update -y
pkg install -y python nodejs
python -m pip install --upgrade pip
python -m pip install termux-diffusion
termux-diffusion install
python -m cinematic_image_engine_v51.runtime_probe