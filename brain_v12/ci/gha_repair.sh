#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p brain_v12/ci-reports
python -m compileall -q brain_v12
command -v ffmpeg >/dev/null 2>&1 && ffmpeg -version | head -n1 > brain_v12/ci-reports/ffmpeg-version.txt || true
command -v ffprobe >/dev/null 2>&1 && ffprobe -version | head -n1 > brain_v12/ci-reports/ffprobe-version.txt || true
python brain_v12/ci/github_actions_repair.py
