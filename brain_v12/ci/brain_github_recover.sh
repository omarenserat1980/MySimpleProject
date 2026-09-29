#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p brain_v12/ci-reports
python -m compileall -q brain_v12
python brain_v12/ci/brain_github_auth.py | tee brain_v12/ci-reports/github-auth.json
