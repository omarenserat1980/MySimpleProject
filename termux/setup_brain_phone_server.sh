#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "=== BRAIN PHONE SERVER bootstrap ==="
pkg update -y
pkg install -y python ffmpeg git

cd "$HOME"
if [ ! -d MySimpleProject ]; then
  git clone https://github.com/omarenserat1980/MySimpleProject.git
fi
cd MySimpleProject

python -m pip install --upgrade pip
python -m pip install -r brain_v7/requirements.txt

export PYTHONPATH="$PWD"
export BRAIN_CLOUD_MODE="phone"
export BRAIN_BLOCK_PRIVATE_NETWORKS="1"
export FACTORY_ALLOW_PRODUCTION="1"
export FACTORY_ALLOW_YOUTUBE_PUBLISH="0"
export FACTORY_REQUIRE_REAL_MEDIA="1"
export FACTORY_ALLOW_LOCAL_FALLBACK="1"
export FACTORY_MEDIA_ROUTE="local_ffmpeg_cinematic"
export FACTORY_OUTPUT_DIR="$PWD/cinematic_output"
export LOCAL_MEDIA_DIR="$PWD/cinematic_output"
export BRAIN_STATE_DIR="$PWD/.brain_state"
export BRAIN_CONTROL_TOKEN="CHANGE_ME"

mkdir -p "$FACTORY_OUTPUT_DIR" "$BRAIN_STATE_DIR"

echo
echo "BRAIN Cloud Hub will listen on 0.0.0.0:8787"
echo "Change BRAIN_CONTROL_TOKEN before exposing it outside your LAN."
echo

python -m uvicorn cloud.api_server:app --host 0.0.0.0 --port 8787
