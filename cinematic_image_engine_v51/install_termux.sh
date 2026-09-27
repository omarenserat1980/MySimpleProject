#!/data/data/com.termux/files/usr/bin/bash
set -e
pkg update -y
pkg install -y python git
python -m pip install --upgrade pip
echo "V5.1 orchestration layer is ready."
echo "Next: configure EB_IMAGE_ADAPTER to your local image generator."
